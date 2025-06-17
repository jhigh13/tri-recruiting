import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import FilePurpose 
from azure.ai.agents.models import BingGroundingTool
from azure.ai.agents.models import FileSearchTool

# Create an Azure AI Client from an endpoint, copied from your Azure AI Foundry project.
# You need to login to Azure subscription via Azure CLI and set the environment variables
project_endpoint = os.environ["PROJECT_ENDPOINT"]  # Ensure the PROJECT_ENDPOINT environment variable is set
conn_id = os.environ["BING_CONNECTION_NAME"]

# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),  # Use Azure Default Credential for authentication
    api_version="latest",
)


bing = BingGroundingTool(connection_id=conn_id)

file_path = "C:\Users\jhigh\Projects\tri-recruiting\etl\match.md"
file = project_client.agents.files.upload_and_poll(file_path=file_path, purpose=FilePurpose.AGENTS)
print(f"Uploaded file, file ID: {file.id}")

vector_store = project_client.agents.create_vector_store_and_poll(file_ids=[file.id], name="my_vectorstore")
print(f"Created vector store, vector store ID: {vector_store.id}")

file_search = FileSearchTool(vector_store_ids=[vector_store.id])

with project_client:
    # Create an agent with the Bing Grounding tool
    agent = project_client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],  # Model deployment name
        name="ValidateSwimBackground",  # Name of the agent
        instructions=
        
        '''Determine if a given NCAA runner has a previous swimming background.
            Given a runner’s profile: first name, last name, college team. Build a query: 'name' + 'college team' + 'track and field'. Find runner's college profile.

            Then create the query: 'name' + 'hometown' + 'SwimCloud'.
            Search for possible matches on SwimCloud, a public swimming results website.

            For each SwimCloud profile you find use the match.md file to calculate a runner's score for a swim background. Do not use your own scoring criteria. 

            Example Input: Christian Jackson, Virginia Tech

            Name:Christian Jackson
            College: Virginia Tech
            Class: Junior
            High School: Colonial Forge
            Hometown: Stafford, VA
            Swimmer: No
            Score: 60
            Match Confidence: High

            Example Input: Chase Atkins, Bellarmine

            Chase Atkins
            College: Bellarmine University
            Class: Redshirt Junior
            High School: Hopkinsville High School 
            Hometown: Hopkinsville, KY
            Swimmer: Yes
            Score: 100
            Match Confidence: High
            ''',
        tools=[file_search.definitions, bing.definitions],
        tool_resources =   # Attach the tool
    )
    print(f"Created agent, ID: {agent.id}")

    # Create a thread for communication
    thread = project_client.agents.threads.create()
    print(f"Created thread, ID: {thread.id}")
    
    # Add a message to the thread
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",  # Role of the message sender
        content="Jett Knight, Air Force",  # Message content
    )
    print(f"Created message, ID: {message['id']}")
    
    # Create and process an agent run
    run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    print(f"Run finished with status: {run.status}")
    
    # Check if the run failed
    if run.status == "failed":
        print(f"Run failed: {run.last_error}")
    
    # Fetch and log all messages
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for message in messages:
        print(f"Role: {message.role}, Content: {message.content}")
    
    # Delete the agent when done
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")
