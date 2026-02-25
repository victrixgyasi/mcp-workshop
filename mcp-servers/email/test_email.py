#!/usr/bin/env python3
import asyncio
import os
import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PYTHON = "/Users/victrixgyasi/Documents/mcp-workshop/fac-mcp/mcp-servers/email/venv/bin/python"
SERVER_SCRIPT = "/Users/victrixgyasi/Documents/mcp-workshop/fac-mcp/mcp-servers/email/email_server.py"


async def main():
    server_params = StdioServerParameters(
        command=SERVER_PYTHON,
        args=[SERVER_SCRIPT],
        env={
            "EMAIL_USER": os.environ["EMAIL_USER"],
            "EMAIL_APP_PASSWORD": os.environ["EMAIL_APP_PASSWORD"],
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get tools from MCP server and convert to Anthropic format
            tools_result = await session.list_tools()
            tools = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                }
                for t in tools_result.tools
            ]
            print(f"Tools available: {[t['name'] for t in tools]}\n")

            client = anthropic.Anthropic()
            messages = [
                {
                    "role": "user",
                    "content": 'Send an email to victrixgyasi@gmail.com with subject "Test from MCP2" and body "This is a test email sent through Claude!"',
                }
            ]

            # Agentic loop
            while True:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    tools=tools,
                    messages=messages,
                )

                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            print(block.text)
                    break

                if response.stop_reason == "tool_use":
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            print(f"Calling tool: {block.name}")
                            print(f"With args: {block.input}\n")
                            result = await session.call_tool(block.name, block.input)
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result.content[0].text if result.content else "",
                                }
                            )

                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})
                else:
                    break


if __name__ == "__main__":
    asyncio.run(main())
