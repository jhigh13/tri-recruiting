from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
from azure.ai.agents.models import FilePurpose

project = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint="https://johnk-mbpfyiuy-eastus2.services.ai.azure.com/api/projects/johnk-mbpfyiuy-eastus2_project")

agent = project.agents.get_agent("asst_0WX84AKx9R2cfqWIuPo5Dl2m")

thread = project.agents.threads.get("thread_Ma4UCUWV6oxqxSzkkTWzi5RM")

message = project.agents.messages.create(
    thread_id=thread.id,
    role="user",
    content="Hi CheckSwimBackgrond"
)

run = project.agents.runs.create_and_process(
    thread_id=thread.id,
    agent_id=agent.id)

if run.status == "failed":
    print(f"Run failed: {run.last_error}")
else:
    messages = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)

    for message in messages:
        if message.text_messages:
            print(f"{message.role}: {message.text_messages[-1].text.value}")