from __future__ import annotations

import asyncio
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.toolbox_toolset import ToolboxToolset
from toolbox_core.protocol import Protocol

from app.config import load_runtime_config
from app.tools.session_tools import (
    clear_last_recommendation,
    get_user_profile_snapshot,
    save_last_recommendation,
    save_user_profile,
)


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "insurance_agent_prompt.txt"


def load_agent_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


class AgentFactory:
    def __init__(self, config) -> None:
        self._config = config

    def create_toolbox(self) -> ToolboxToolset:
        return ToolboxToolset(
            server_url=self._config.toolbox_server_url,
            protocol=Protocol.MCP_LATEST,
        )

    def build_tools(self) -> list[object]:
        return [
            get_user_profile_snapshot,
            save_user_profile,
            save_last_recommendation,
            clear_last_recommendation,
            self.create_toolbox(),
        ]

    def create(self) -> Agent:
        return Agent(
            name=self._config.app_name,
            model=self._config.model_name,
            instruction=load_agent_prompt(),
            tools=self.build_tools(),
        )


def create_agent(config=None) -> Agent:
    runtime_config = config or load_runtime_config()
    return AgentFactory(runtime_config).create()


root_agent = create_agent()


# async def main():
#     config = load_runtime_config()
#     agent = create_agent(config)

#     print("insurance_recommendation_agent initialized.")
#     print("Session tools attached.")
#     print("ToolboxToolset attached.")
#     print("Prompt loaded from file.")
#     print(f"App name: {config.app_name}")
#     print(f"Toolbox URL: {config.toolbox_server_url}")
#     print(f"Session DB URI: {config.session_db_uri}")
#     print(agent)


# if __name__ == "__main__":
#     asyncio.run(main())
