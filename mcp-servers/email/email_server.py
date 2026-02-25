#!/usr/bin/env python3
import asyncio
import email as email_lib
import imaplib
import os
import smtplib
import time
from email.header import decode_header
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
        types.Tool(
            name="get_unread_emails",
            description="Fetch unread emails from Gmail inbox",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to fetch (default 10)",
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="create_draft_reply",
            description="Generate an AI draft reply for an email and save it to Gmail drafts",
            inputSchema={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "The email message ID from get_unread_emails",
                    },
                    "from_address": {
                        "type": "string",
                        "description": "Sender of the original email",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject of the original email",
                    },
                    "body": {
                        "type": "string",
                        "description": "Body of the original email",
                    },
                },
                "required": ["email_id", "from_address", "subject", "body"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "send_email":
        return await handle_send_email(arguments)
    elif name == "get_unread_emails":
        return await handle_get_unread_emails(arguments)
    elif name == "create_draft_reply":
        return await handle_create_draft_reply(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_send_email(arguments: dict) -> list[types.TextContent]:
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


async def handle_get_unread_emails(arguments: dict) -> list[types.TextContent]:
    email_user = os.environ["EMAIL_USER"]
    email_password = os.environ["EMAIL_APP_PASSWORD"]
    max_results = arguments.get("max_results", 10)

    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(email_user, email_password)
        imap.select("INBOX")

        _, message_ids = imap.search(None, "UNSEEN")
        ids = message_ids[0].split()

        if not ids:
            return [types.TextContent(type="text", text="No unread emails found.")]

        ids = ids[-max_results:]
        emails = []

        for msg_id in ids:
            _, msg_data = imap.fetch(msg_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw_email)

            # Decode subject
            subject_parts = decode_header(msg["Subject"] or "")
            subject = ""
            for part, enc in subject_parts:
                if isinstance(part, bytes):
                    subject += part.decode(enc or "utf-8", errors="replace")
                else:
                    subject += part

            # Get plain text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        body = payload.decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
                        break
            else:
                payload = msg.get_payload(decode=True)
                body = payload.decode(
                    msg.get_content_charset() or "utf-8", errors="replace"
                )

            emails.append(
                f"ID: {msg_id.decode()}\n"
                f"From: {msg['From']}\n"
                f"Subject: {subject}\n"
                f"Body:\n{body[:500]}"
            )

    result = "\n\n---\n\n".join(emails)
    return [types.TextContent(type="text", text=result)]


async def handle_create_draft_reply(arguments: dict) -> list[types.TextContent]:
    email_user = os.environ["EMAIL_USER"]
    email_password = os.environ["EMAIL_APP_PASSWORD"]

    from_address = arguments["from_address"]
    subject = arguments["subject"]
    body = arguments["body"]

    # Use MCP sampling to generate the reply via the client's Claude instance
    sampling_result = await server.request_context.session.create_message(
        messages=[
            types.SamplingMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=(
                        f"Please write a professional reply to this email:\n\n"
                        f"From: {from_address}\n"
                        f"Subject: {subject}\n\n"
                        f"{body}"
                    ),
                ),
            )
        ],
        max_tokens=1024,
    )

    draft_text = sampling_result.content.text

    # Save the draft to Gmail via IMAP
    msg = MIMEText(draft_text, "plain")
    msg["From"] = email_user
    msg["To"] = from_address
    msg["Subject"] = f"Re: {subject}"

    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(email_user, email_password)
        imap.append(
            "[Gmail]/Drafts",
            "\\Draft",
            imaplib.Time2Internaldate(time.time()),
            msg.as_bytes(),
        )

    return [
        types.TextContent(
            type="text",
            text=f"✓ Draft reply saved to Gmail Drafts.\n\nGenerated reply:\n{draft_text}",
        )
    ]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
