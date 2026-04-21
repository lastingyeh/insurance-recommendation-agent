import asyncio

from toolbox_adk import ToolboxToolset, CredentialStrategy
from toolbox_core.protocol import Protocol


async def main():
    toolset = ToolboxToolset(
        server_url="http://127.0.0.1:5000",
        protocol=Protocol.MCP_LATEST,
        credentials=CredentialStrategy.toolbox_identity(),
    )

    tools = await toolset.get_tools()
    print("Loaded tools:")
    for tool in tools:
        print("-", getattr(tool, "name", repr(tool)))


if __name__ == "__main__":
    asyncio.run(main())
