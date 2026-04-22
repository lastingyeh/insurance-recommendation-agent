from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.toolbox_toolset import ToolboxToolset
from toolbox_core.protocol import Protocol

from app.tools.insurance_tools import (
    search_products_by_profile,
    get_product_detail,
    get_recommendation_rules,
    summarize_user_profile,
)

APP_NAME = "insurance_recommendation_agent"


def load_prompt() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "insurance_agent_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")


def create_agent() -> Agent:
    toolbox = ToolboxToolset(
        server_url="http://127.0.0.1:5000",
        protocol=Protocol.MCP,
    )

    return Agent(
        name=APP_NAME,
        model="gemini-2.5-flash",
        instruction=load_prompt(),
        tools=[
            # summarize_user_profile,
            # search_products_by_profile,
            # get_product_detail,
            # get_recommendation_rules,
            toolbox,
        ],
    )


root_agent = create_agent()


def main():
    print(f"{APP_NAME} initialized.")
    print("ToolboxToolset attached.")
    print("Prompt loaded from file.")
    print(root_agent)


if __name__ == "__main__":
    main()
