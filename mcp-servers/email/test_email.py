#!/usr/bin/env python3
import asyncio
import os
import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import mcp.types as types

SERVER_PYTHON = "/Users/victrixgyasi/Documents/mcp-workshop/fac-mcp/mcp-servers/email/venv/bin/python"
SERVER_SCRIPT = "/Users/victrixgyasi/Documents/mcp-workshop/fac-mcp/mcp-servers/email/email_server.py"

anthropic_client = anthropic.Anthropic()


async def sampling_callback(context, params):
    """Handle sampling requests from the MCP server by calling the Anthropic API."""
    messages = [
        {
            "role": msg.role,
            "content": msg.content.text,
        }
        for msg in params.messages
    ]

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=params.maxTokens,
        messages=messages,
    )

    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(type="text", text=response.content[0].text),
        model=response.model,
        stopReason=response.stop_reason,
    )


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
        async with ClientSession(
            read, write, sampling_callback=sampling_callback
        ) as session:
            await session.initialize()

            # Step 1: Fetch unread emails
            print("Fetching unread emails...\n")
            emails_result = await session.call_tool("get_unread_emails", {"max_results": 1})
            emails_text = emails_result.content[0].text
            print(emails_text)
            print("\n" + "=" * 50 + "\n")

            # Parse the first email from the returned text
            lines = emails_text.strip().split("\n")
            email_id = lines[0].replace("ID: ", "").strip()
            from_address = lines[1].replace("From: ", "").strip()
            subject = lines[2].replace("Subject: ", "").strip()
            body = "\n".join(lines[4:])  # everything after "Body:"

            # Step 2: Create a draft reply (triggers MCP sampling)
            print(f"Creating draft reply for: {subject}\n")
            draft_result = await session.call_tool(
                "create_draft_reply",
                {
                    "email_id": email_id,
                    "from_address": from_address,
                    "subject": subject,
                    "body": body,
                },
            )
            print(draft_result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
