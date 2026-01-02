import sys
from contextlib import AsyncExitStack
from typing import Any, Awaitable, Callable, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    """MCP client to interact with MCP server.

    Usage:
        async with MCPClient(server_path) as client:
            # Call client methods here...
    """

    def __init__(self, server_path: str):
        self.session: Optional[ClientSession] = None
        self.server_path = server_path
        self.exit_stack = AsyncExitStack()

    async def __aenter__(self) -> Any:
        cls = type(self)
        cls.session = await self._connect_to_server()
        return self

    async def __aexit__(self, *_) -> None:
        await self.exit_stack.aclose()

    async def connect_to_server(self):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = self.server_path.endswith('.py')
        if not is_python:
            raise ValueError("Server script must be a .py")

        server_params = StdioServerParameters(
            command="python",
            args=[self.server_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

    async def list_all_members(self) -> None:
        """List all available tools, prompts, and resources."""
        print("MCP Server Members")
        print("=" * 50)

        sections = {
            "tools": self.session.list_tools,
            "prompts": self.session.list_prompts,
            "resources": self.session.list_resources,
        }
        for section, listing_method in sections.items():
            await self._list_section(section, listing_method)

        print("\n" + "=" * 50)

    async def _list_section(
        self,
        section: str,
        list_method: Callable[[], Awaitable[Any]],
    ) -> None:
        try:
            items = getattr(await list_method(), section)
            if items:
                print(f"\n{section.upper()} ({len(items)}):")
                print("-" * 30)
                for item in items:
                    description = item.description or "No description"
                    print(f" > {item.name} - {description}")
            else:
                print(f"\n{section.upper()}: None available")
        except Exception as e:
            print(f"\n{section.upper()}: Error - {e}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()