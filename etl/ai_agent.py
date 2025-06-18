import os
import sys
import json
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
    FunctionTool,
    ToolSet,
)

sys.path.append(str(Path(__file__).parent.parent))

# Create an Azure AI Client from an endpoint, copied from your Azure AI Foundry project.
project_endpoint = os.environ["PROJECT_ENDPOINT"]  # Ensure the PROJECT_ENDPOINT environment variable is set

# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),  # Use Azure Default Credential for authentication
    #api_version="latest",
)


def use_agent(runner_id: id) -> str:
    agent = project_client.agents.get_agent("asst_yGc1n6WeUULxruHX3TCbG61U")

    # Create a new thread for the agent interaction
    thread = project_client.agents.threads.create()

    session = get_db_session()
    runner = session.query(Runner).filter(Runner.runner_id == runner_id).first()
    runner_info = f"{runner.first_name} {runner.last_name}, College: {runner.college_team}"

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
    for message in messages:
        if message.role == "assistant":
            return message.content
    
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
        runner.class_year = agent_output.get("class")
        session.commit()
        print(f"Runner {runner.id} updated with agent output.")
    except Exception as e:
        session.rollback()
        print(f"Error updating runner: {e}")
    finally:
        session.close()
        
def parse_agent_response(response):
    """
    Extract and parse the agent's JSON output from the response list.
    """
    if isinstance(response, list) and response:
        msg = response[0]
        json_str = msg.get('text', {}).get('value', None)
        if json_str:
            return json.loads(json_str)
    return None

def main():
    next_runner = get_next_runner_id()
    if next_runner != -1:

        print(f"Processing runner: {next_runner}")
        response = use_agent(next_runner)
        response = json.loads(response)
        agent_output = parse_agent_response(response)
        if agent_output:
            update_runner_with_agent_output(next_runner, agent_output)
            print(f"AI Agent Response: {agent_output}")
        else:
            print("Could not parse agent output.")
    else:
        print("No runners to process.")

if __name__ == "__main__":
    main()