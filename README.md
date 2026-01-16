# Exercise 2: Build an Email Assistant MCP Server

## Your Challenge

Extend your email server to fetch unread emails and generate AI-powered draft replies using MCP sampling.

Feel free to get creative! If you'd prefer to build something different that solves a problem you care about, go for it. The goal is to understand how MCP servers work by building something useful.

## What You're Building

An MCP server that:

1. Fetches your unread emails from Gmail
2. Generates draft replies using Claude (via MCP sampling)
3. Saves those drafts in Gmail, ready for you to review and send

## Prerequisites

- Completed Exercise 1 (email server with `send_email` tool working)
- Gmail App Password already configured

---

## Part 1: Fetch Unread Emails

**Tool to build:** `get_unread_emails`

Connect to Gmail and retrieve unread emails. You used `smtplib` for sending in Exercise 1; now you'll need `imaplib` for reading.

**Expected behaviour:**
- Connect to Gmail via IMAP
- Fetch unread messages
- Return message ID, sender, subject, and body for each

---

## Part 2: Generate Draft Replies Using Sampling

**Tool to build:** `create_draft_reply`

Takes an email message ID, uses MCP sampling to request a reply from the client's Claude instance, then saves it as a draft in Gmail.

**Expected behaviour:**
- Accept an email ID and email content as parameters
- Send a sampling request to the MCP client asking Claude to generate a reply
- Receive the generated reply
- Save it as a draft in Gmail
- Return confirmation

**Note:** MCP Inspector does not support sampling. You'll need to test this part with Claude Desktop.

---

## Useful Resources

- [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) - Browser-based debugging tool (Part 1 only, doesn't support sampling)
- [FastMCP Quickstart](https://gofastmcp.com/getting-started/quickstart) - Python framework that eliminates MCP boilerplate
- [MCP Sampling Documentation](https://modelcontextprotocol.io/docs/concepts/sampling) - How servers request LLM completions from clients

---

## Stretch Goals

### Smarter drafts with more context

The real power of MCP is connecting multiple data sources. What context would help Claude write better replies?

Some ideas:
- Previous emails with this sender
- A style guide from Notion or Google Docs
- Company FAQ or knowledge base
- Your calendar for availability
- CRM data about the sender

You could build these as additional tools, or connect to existing MCP servers.

Get creative. What context would make *your* email replies better?