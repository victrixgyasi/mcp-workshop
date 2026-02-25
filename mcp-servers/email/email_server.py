#!/usr/bin/env python3
import asyncio
import os
import smtplib
from email.mime.text import MIMEText

from mcp.server import Server
import mcp.server.stdio
import mcp.types as types

server = Server("email-server")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="send_email",
            description="Send an email",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"},
                },
                "required": ["to", "subject", "body"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "send_email":
        raise ValueError(f"Unknown tool: {name}")

    email_user = os.environ["EMAIL_USER"]
    email_password = os.environ["EMAIL_APP_PASSWORD"]

    msg = MIMEText(arguments["body"], "plain")
    msg["From"] = email_user
    msg["To"] = arguments["to"]
    msg["Subject"] = arguments["subject"]

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(email_user, email_password)
        smtp.send_message(msg)

    return [types.TextContent(type="text", text=f"✓ Email sent to {arguments['to']}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())