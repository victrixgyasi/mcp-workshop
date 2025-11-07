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
- Anthropic API key

## Part 1: Fetch Unread Emails

**Install dependencies:**
```bash
pip install imapclient email-reply-parser
```

**Tool to build:**
`get_unread_emails` - Connects to Gmail via IMAP and retrieves unread emails with their content


## Part 2: Generate Draft Replies

**Install dependencies:**
```bash
pip install anthropic
```

**Tool to build:**
`create_draft_reply` - Takes an email message ID, uses Claude to generate a contextual reply, saves it as a draft in Gmail