# Build an Email MCP Server

## Your Challenge

Build an MCP server that fetches unread emails from Gmail and generates AI-powered draft replies.

**Feel free to get creative!** If you'd prefer to build a different MCP server that solves a problem you care about, go for it. This exercise is a framework the goal is to understand how MCP servers work by building something useful.

## What You're Building (Suggested Project)

An MCP server that:
1. Fetches your unread emails from Gmail
2. Generates AI-powered draft replies using Claude
3. Saves those drafts in Gmail, ready for you to review and send

## Prerequisites

- Completed the `exercise-1` branch
- Gmail account with App Password

## Part 1: Fetch Unread Emails

**Tool to build:**
`get_unread_emails` - Connects to Gmail and retrieve unread emails

## Part 2: Generate Draft Replies Using Sampling

**Tool to build:**
`create_draft_reply`

Takes an email message ID, uses **MCP sampling** to request a reply from the client's Claude instance, then saves it as a draft in Gmail.

**Expected behavior:**
- Accept an email ID and email content as parameters
- Send a **sampling request** to the MCP client with a prompt asking Claude to generate a reply
- Receive the generated reply from the client
- Connect to Gmail via SMTP/IMAP
- Save the generated reply as a draft in the correct email thread
- Return confirmation

## Useful Resources

[MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector): A browser-based debugging tool that lets you send requests to your server and inspect the responses. Invaluable when your tools aren't behaving as expected.

[FastMCP Quickstart](https://gofastmcp.com/getting-started/welcome): A Python framework that eliminates MCP boilerplate. Instead of manually writing JSON schemas for your tools, you define regular Python functions with type hints—FastMCP generates the schemas automatically.