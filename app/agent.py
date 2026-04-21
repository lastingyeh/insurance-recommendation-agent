from pathlib import Path
from dotenv import load_dotenv

from google.adk.agents import Agent
from toolbox_adk import ToolboxToolset, CredentialStrategy
from toolbox_core.protocol import Protocol

load_dotenv()

APP_NAME = "insurance_recommendation_agent"


def load_prompt() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "insurance_agent_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")


toolbox = ToolboxToolset(
    server_url="http://127.0.0.1:5000",
    protocol=Protocol.MCP,
    credentials=CredentialStrategy.toolbox_identity(),
)

root_agent = Agent(
    name=APP_NAME,
    model="gemini-2.5-flash",
    instruction=load_prompt(),
    tools=[toolbox],
)
