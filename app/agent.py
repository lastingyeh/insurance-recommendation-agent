import asyncio
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.toolbox_toolset import ToolboxToolset
from toolbox_core.protocol import Protocol


from app.config import AppRuntimeConfig, load_runtime_config
from app.tools.session_tools import (
    clear_last_recommendation,
    get_user_profile_snapshot,
    save_last_recommendation,
    save_user_profile,
)

APP_CONFIG = load_runtime_config()


def load_prompt() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "insurance_agent_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")


def create_agent(config: AppRuntimeConfig | None = None):
    runtime_config = config or APP_CONFIG
    toolbox = ToolboxToolset(
        server_url=runtime_config.toolbox_server_url,
        protocol=Protocol.MCP,
    )

    agent = Agent(
        name=runtime_config.app_name,
        model=runtime_config.model_name,
        instruction=load_prompt(),
        tools=[
            get_user_profile_snapshot,
            save_user_profile,
            save_last_recommendation,
            clear_last_recommendation,
            toolbox,
        ],
    )
    return agent


root_agent = create_agent(APP_CONFIG)


async def main():
    print("insurance_recommendation_agent initialized.")
    print("Session tools attached.")
    print("ToolboxToolset attached.")
    print("Prompt loaded from file.")
    print(f"App name: {APP_CONFIG.app_name}")
    print(f"Toolbox URL: {APP_CONFIG.toolbox_server_url}")
    print(f"Session DB URI: {APP_CONFIG.session_db_uri}")
    print(root_agent)


if __name__ == "__main__":
    asyncio.run(main())
