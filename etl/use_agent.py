import os
import sys
import json
import time
from pathlib import Path
from db.db_connection import get_db_session
from db.models import Runner

from typing import List, Any

from opentelemetry import trace
#from azure.monitor.opentelemetry import configure_azure_monitor
from azure.ai.projects import AIProjectClient
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential


sys.path.append(str(Path(__file__).parent.parent))
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")

from sqlalchemy import inspect
session = get_db_session()
engine = session.get_bind()
if engine.dialect.name == "sqlite":
    print(f"Connected SQLite DB file: {engine.url.database}")
session.close()

def use_agent(runner_id: int) -> str:
    project_endpoint = os.environ["PROJECT_ENDPOINT"]  # Ensure the PROJECT_ENDPOINT environment variable is set
    

    agents_client = AgentsClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    session = get_db_session()
    runner = session.query(Runner).filter(Runner.runner_id == runner_id).first()
    runner_info = f"{runner.first_name} {runner.last_name}, {runner.college_team}"

    with agents_client:
        agent = agents_client.get_agent("asst_yGc1n6WeUULxruHX3TCbG61U") 
    
        # Create a new thread for the agent interaction
        thread = agents_client.threads.create()

        # Create a user message with the runner information
        message = agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content=runner_info,
        )
        
        # Run the agent with the created thread
        run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)

        # Check if the run was successful
        if run.status == "failed":
            return f"Run failed: {run.last_error}"
        
        # Fetch and return the assistant's response
        messages = agents_client.messages.list(thread_id=thread.id)

        #response_message = project_client.messages.get_last_message_by_role(thread_id=thread.id, role="assistant")
        for message in messages:
            if message.role == "assistant":
                #print(f"Assistant response: {message.content[0]['text']['value']}")
                response = json.loads(message.content[0]['text']['value'])
                #project_client.agents.threads.delete(thread_id=thread.id)
                return response
        
        #project_client.agents.threads.delete(thread_id=thread.id)
        return "No assistant response found."

def get_next_runner_id() -> int:
    """
    Fetch the next runner from the database that needs AI processing.
    
    This function should connect to your database and retrieve a runner
    that has not yet been processed by the AI agent.
    
    Returns:
        str: A string containing the runner's information.
    """
    session = get_db_session()
    runner = session.query(Runner).filter(Runner.swimmer == None).first()
    if runner:
        return runner.runner_id
    return -1

def build_user_query(runner_id: int) -> str:
    """
    Build a user query string for the AI agent based on the runner's information.

    Args:
        runner_id (int): The ID of the runner.

    Returns:
        str: A formatted string containing the runner's information.
    """
    session = get_db_session()
    runner = session.query(Runner).filter(Runner.id == runner_id).first()
    if runner:
        return f"{runner.first_name} {runner.last_name}, {runner.college_team}"
    return "Runner not found."

def update_runner_with_agent_output(runner_id: int, agent_output: dict) -> None:
    """
    Update the runner's record in the database with AI agent output.

    Args:
        agent_output (dict): Dictionary with keys: name, college, class, high_school, hometown, swimmer, score, match_confidence.
    """
    session = get_db_session()
    try:
        # Find the runner by id
        runner = session.query(Runner).filter(
            Runner.runner_id == runner_id,
        ).first()
        if not runner:
            print(f"No runner found for ID {runner_id}")
            return
        runner.high_school = agent_output.get("high_school")
        runner.hometown = agent_output.get("hometown")
        runner.swimmer = agent_output.get("swimmer")
        runner.score = agent_output.get("score")
        runner.match_confidence = agent_output.get("match_confidence")
        session.commit()
        print(f"Runner {runner.runner_id} updated with agent output.")
    except Exception as e:
        session.rollback()
        print(f"Error updating runner: {e}")
    finally:
        session.close()
    

def append_training_example(system_prompt: str, user_message: str, assistant_response: dict, jsonl_path: str = "etl/data/training_data.jsonl") -> None:
    """
    Append a training example to the JSONL file in the required structure.
    """
    # Format the assistant's response as a readable string
    response_lines = [
        f"Name: {assistant_response.get('name', '')}",
        f"College: {assistant_response.get('college', '')}",
        f"High School: {assistant_response.get('high_school', '')}",
        f"Hometown: {assistant_response.get('hometown', '')}",
        f"Swimmer: {assistant_response.get('swimmer', '')}",
        f"Score: {assistant_response.get('score', '')}",
        f"Match Confidence: {assistant_response.get('match_confidence', '')}"
    ]
    assistant_content = "\n" + "\n".join(response_lines)
    entry = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_content}
        ]
    }
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def main():

    with open("etl/system_prompt.txt", "r", encoding="utf-8") as f:
        instructions = f.read().strip()
    
    processed = 0
    max_batch = 10
    while processed < max_batch:
        next_runner = get_next_runner_id()
        if next_runner != -1:
            print(f"Processing runner: {next_runner}")
            # Build user message for training data
            session = get_db_session()
            runner = session.query(Runner).filter(Runner.runner_id == next_runner).first()
            user_message = f"{runner.first_name} {runner.last_name}, {runner.college_team}"
            agent_output = use_agent(next_runner)
            if agent_output:
                try:
                    update_runner_with_agent_output(next_runner, agent_output)
                    print(f"AI Agent Response: {agent_output}")
                    # Save to training data
                    append_training_example(instructions, user_message, agent_output)
                except Exception as e:
                    print(f"Could not parse agent output: {e}")
            else:
                print("No agent response.")
            processed += 1
            if processed < max_batch:
                print("Waiting 40 seconds before next runner...")
                time.sleep(50)
        else:
            print("No runners to process. Exiting.")
            break
    print(f"Batch complete. Processed {processed} runner(s).")

if __name__ == "__main__":
    main()