import asyncio
import json
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from baml_client.sync_client import b
from baml_client.types import ChatMessage, ChatResponse, ToolCall, MCPTool

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.baml = b

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using BAML and available tools"""
        messages = [ChatMessage(role="user", content=query)]

        response = await self.session.list_tools()
        available_tools = [MCPTool(
            name=tool.name,
            description=tool.description or "",
            input_schema=str(tool.inputSchema)
        ) for tool in response.tools]

        # First BAML call with tools
        response = self.baml.ChatWithLLM(
            messages=messages,
            available_tools=available_tools
        )

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        if isinstance(response, ChatResponse):
            print(f"Response is a ChatResponse: {response.content}")
            final_text.append(response.content)
        
        if isinstance(response, ToolCall):
            print(f"Response is a ToolCall: {response.name}")
            tool_name = response.name
            tool_args = json.loads(response.args)
            
            # Execute tool call
            result = await self.session.call_tool(tool_name, tool_args)
            tool_results.append({"call": tool_name, "result": result})
            final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

            # Continue conversation with tool results
            messages.append(ChatMessage(
                role="assistant",
                content=f"The tool {tool_name} returned: {result}"
            ))

            # Get next response from BAML
            final_response = self.baml.ChatWithLLM(
                messages=messages,
                available_tools=available_tools
            )

            if isinstance(final_response, ChatResponse):
                final_text.append(final_response.content)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())