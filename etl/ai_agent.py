import os
import sys
import json
import time
from pathlib import Path
from db.db_connection import get_db_session
from db.models import Runner

from typing import List, Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import (
    BingGroundingTool,
    FilePurpose,
    FileSearchTool,
    ToolSet,
)

sys.path.append(str(Path(__file__).parent.parent))

# Create an Azure AI Client from an endpoint, copied from your Azure AI Foundry project.
project_endpoint = os.environ["PROJECT_ENDPOINT"]  # Ensure the PROJECT_ENDPOINT environment variable is set

# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),  # Use Azure Default Credential for authentication
    api_version="latest",
)

# Get Bing connection using the correct argument name
bing_connection = project_client.connections.get(os.environ["BING_CONNECTION_NAME"])
conn_id = bing_connection.id
bing_tool = BingGroundingTool(connection_id=conn_id)
print(conn_id)

file_path = "./etl/match.md"

file = project_client.agents.files.upload_and_poll(file_path=file_path, purpose=FilePurpose.AGENTS)
print(f"Uploaded file, file ID: {file.id}")

vector_store = project_client.agents.vector_stores.create_and_poll(file_ids=[file.id], name="my_vectorstore")
print(f"Created vector store, vector store ID: {vector_store.id}")
file_search = FileSearchTool(vector_store_ids=[vector_store.id])

# Use a list of tool model objects, not ToolSet
TOOLS = [bing_tool, file_search]


def use_agent(runner_id: id) -> str:

    system_prompt = (
        """Determine if a given NCAA runner has a previous swimming background.
        Given a runner's profile: first name, last name, college team.
        1. Build a query: 'name' + 'college team' + 'track and field'. Find runner's college profile using Bing Search. 
        2. Create the query: 'name' + 'hometown' + 'SwimCloud'. Then use Bing Search to look for possible matches on SwimCloud, a public swimming results website.
        3. Use file search tool and the match.md file to calculate a match score for the runner, decide if the runner has a swim background and evaluate the strength of your decision. You must use the point values and criteria exactly as described in match.md. For each match, add up the points only from the criteria that are explicitly met. Do not round up, estimate, or invent new scoring rules
        4. Respond ONLY with a valid JSON object:
        {
        "name": ...,
        "college": ...,
        "high_school": ...,
        "hometown": ...,
        "swimmer": ...,
        "score": ...,
        "match_confidence": ...
        }
        No extra text or formatting.

        Example:
        Input: Christian Jackson, Virginia Tech
        Output:
        {"name": "Christian Jackson", "college": "Virginia Tech", "high_school": "Colonial Forge", "hometown": "Stafford, VA", "swimmer": "No", "score": 60, "match_confidence": "High"}
    """)
    
    agent = project_client.agents.create_agent(
        name = "ValidateSwimBackground",
        instructions= system_prompt,
        temperature= 0.4,
        tools=TOOLS  # Pass as 'tools', not 'toolset'
    )

    # Create a new thread for the agent interaction
    thread = project_client.agents.threads.create()

    session = get_db_session()
    runner = session.query(Runner).filter(Runner.runner_id == runner_id).first()
    runner_info = f"{runner.first_name} {runner.last_name}, {runner.college_team}"

    # Create a user message with the runner information
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=runner_info,
    )
    
    # Run the agent with the created thread
    run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)

    # Check if the run was successful
    if run.status == "failed":
        return f"Run failed: {run.last_error}"
    
    # Fetch and return the assistant's response
    messages = project_client.agents.messages.list(thread_id=thread.id)

    #response_message = project_client.messages.get_last_message_by_role(thread_id=thread.id, role="assistant")
    for message in messages:
        if message.role == "assistant":
            #print(f"Assistant response: {message.content[0]['text']['value']}")
            response = json.loads(message.content[0]['text']['value'])
            project_client.agents.threads.delete(thread_id=thread.id)
            return response
    
    project_client.agents.threads.delete(thread_id=thread.id)
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
        return f"{runner.first_name} {runner.last_name}, College: {runner.college_team}"
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
    system_prompt = (
        """Determine if a given NCAA runner has a previous swimming background.
        Given a runner's profile: first name, last name, college team.
        1. Build a query: 'name' + 'college team' + 'track and field'. Find runner's college profile. 
        2. Create the query: 'name' + 'hometown' + 'SwimCloud'.
        3. Search for possible matches on SwimCloud, a public swimming results website.
        4. Use file search and the match.md file to calculate a match score for the runner. You must use the point values and criteria exactly as described in match.md. For each match, add up the points only from the criteria that are explicitly met. Do not round up, estimate, or invent new scoring rules
        5. Respond ONLY with a valid JSON object:
        {
        "name": ...,
        "college": ...,
        "high_school": ...,
        "hometown": ...,
        "swimmer": ...,
        "score": ...,
        "match_confidence": ...
        }
        No extra text or formatting.

        Example:
        Input: Christian Jackson, Virginia Tech
        Output:
        {"name": "Christian Jackson", "college": "Virginia Tech", "high_school": "Colonial Forge", "hometown": "Stafford, VA", "swimmer": "No", "score": 50, "match_confidence": "High"}
    """)
    processed = 0
    max_batch = 200
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
                    append_training_example(system_prompt, user_message, agent_output)
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