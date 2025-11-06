# Building a Simple Email MCP Server for Claude Desktop

This guide will walk you through creating a Model Context Protocol (MCP) server that allows Claude Desktop to send emails on your behalf. The aim here is to build a sense of what MCP can do for us and some boilerplate to get us started.

## What You'll Build

An MCP server is a programme that extends Claude's capabilities by giving it access to tools. In this case, we're building a server that provides Claude with a `send_email` tool, allowing it to send emails through Gmail.

## Prerequisites

- **Claude Desktop** installed on your computer
- **Python 3.10 or higher** installed
- A **Gmail account** (we'll use Gmail's SMTP server)

## Step 1: Set Up Your Project Directory

First, create a dedicated folder for your MCP server:

```bash
mkdir -p ~/mcp-servers/email
cd ~/mcp-servers/email
```

## Step 2: Create a Virtual Environment

A virtual environment keeps your project's dependencies isolated from other Python projects:

```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your command prompt, indicating the virtual environment is active.

## Step 3: Install Required Dependencies

With your virtual environment activated, install the MCP Python SDK:

```bash
pip install mcp
```

This installs the Model Context Protocol library that allows your server to communicate with Claude Desktop.

## Step 4: Create the Server Code

Create a file called `email_server.py` in your project directory and paste the following code:

```python
#!/usr/bin/env python3

import asyncio
import os
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


async def send_email(to: str, subject: str, body: str):
    email_user = os.environ['EMAIL_USER']
    email_password = os.environ['EMAIL_APP_PASSWORD']
    
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)


server = Server("email-server")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
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
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "send_email":
        to = arguments["to"]
        subject = arguments["subject"]
        body = arguments["body"]
        
        await send_email(to, subject, body)
        return [types.TextContent(type="text", text=f"✓ Email sent to {to}")]
    
    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="email-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
```

### Understanding the Code

- **`send_email()` function**: Uses Python's built-in SMTP library to send emails through Gmail
- **`@server.list_tools()`**: Tells Claude what tools are available and what parameters they need
- **`@server.call_tool()`**: Handles the actual execution when Claude decides to use a tool
- **`main()`**: Sets up the communication channel between your server and Claude Desktop

## Step 5: Set Up Gmail App Password

For security reasons, Gmail requires an "App Password" rather than your regular password:

1. Go to your Google Account settings at [myaccount.google.com](https://myaccount.google.com)
2. Navigate to **Security** in the left sidebar
3. Enable **2-Step Verification** if you haven't already (this is required for App Passwords)
4. Once 2FA is enabled, go back to **Security**
5. Scroll down to "How you sign in to Google"
6. Click on **App passwords** (or search for "App passwords" in settings)
7. You may need to sign in again
8. Select **Mail** for the app and **Other** for the device
9. Name it something like "MCP Email Server"
10. Click **Generate**
11. **Copy the 16-character password** that appears (it will look like `abcd efgh ijkl mnop`)
12. **Save this password somewhere safe** - you won't be able to see it again

## Step 6: Configure Claude Desktop

Now you need to tell Claude Desktop about your new MCP server.

### Find Your Config File

The location depends on your operating system:

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Edit the Config File

Open the config file in a text editor. If the file doesn't exist yet, create it.

Add the following configuration (or add to the existing `mcpServers` section if you already have other servers):

```json
{
  "mcpServers": {
    "email": {
      "command": "/full/path/to/your/venv/bin/python",
      "args": ["/full/path/to/your/email_server.py"],
      "env": {
        "EMAIL_USER": "your-email@gmail.com",
        "EMAIL_APP_PASSWORD": "your-16-char-app-password"
      }
    }
  }
}
```

### Get Your Full Paths

To find the exact paths you need:

**For the Python path:**
```bash
cd ~/mcp-servers/email
source venv/bin/activate
which python
```

This will output something like `/Users/yourusername/mcp-servers/email/venv/bin/python`

**For the script path:**
```bash
pwd
```

This will show your current directory. Then append `/email_server.py` to it.

### Example Configuration

Here's what a complete config might look like:

```json
{
  "mcpServers": {
    "email": {
      "command": "/Users/izaak/mcp-servers/email/venv/bin/python",
      "args": ["/Users/izaak/mcp-servers/email/email_server.py"],
      "env": {
        "EMAIL_USER": "izaak@example.com",
        "EMAIL_APP_PASSWORD": "abcd efgh ijkl mnop"
      }
    }
  }
}
```

**Important notes:**
- Replace all paths with your actual full paths
- Replace the email with your Gmail address
- Replace the app password with the one you generated (remove spaces)
- Use forward slashes (`/`) even on Windows in the JSON file
- Make sure there are no trailing commas in your JSON

## Step 7: Restart Claude Desktop

Quit Claude Desktop completely (don't just close the window - actually quit the application) and then reopen it.

## Step 8: Test Your Server

Open a new conversation in Claude Desktop and try:

```
Send an email to [YOUR EMAIL] with the subject "Test from MCP" and body "This is a test email sent through Claude!"
```

If everything is set up correctly, you should see Claude use the `send_email` tool and confirm that the email was sent.

## Troubleshooting

### "ModuleNotFoundError: No module named 'mcp'"

This means the MCP library isn't installed in the Python environment that Claude is using. Make sure:
1. Your virtual environment is activated when you run `pip install mcp`
2. Your config file points to the Python executable inside your `venv/bin/` folder

### "Can't open file"

The path in your config file is incorrect. Double-check:
1. The file `email_server.py` actually exists at that location
2. You're using the full absolute path (starting with `/` on macOS/Linux or `C:\` on Windows)
3. There are no typos in the path

### "Authentication failed" or "SMTP error"

Your Gmail credentials might be incorrect. Verify:
1. You're using your Gmail address (not another email service)
2. You're using the App Password, not your regular Gmail password
3. The App Password has no spaces (should be 16 characters altogether)
4. 2-Factor Authentication is enabled on your Google account

### Check the Logs

Claude Desktop keeps logs that can help diagnose issues:

**macOS:**
```
~/Library/Logs/Claude/mcp*.log
```

Look for recent log files and check for error messages.

## How It Works

1. **Claude Desktop starts your server**: When Claude launches, it runs your Python script as a subprocess
2. **Communication via stdio**: Your server and Claude communicate through standard input/output
3. **Tool discovery**: Claude asks your server what tools it has available (via `list_tools`)
4. **Tool execution**: When Claude wants to send an email, it calls your `send_email` tool with the appropriate parameters
5. **Results return**: Your server sends the email and reports back success or failure

## Key Concepts Recap

- **MCP Server**: A programme that provides tools to Claude
- **Tools**: Functions that Claude can call (like `send_email`)

You've now built your first MCP server and extended Claude's capabilities. This same pattern can be used to connect any AI application to databases, APIs, file systems, and much more.

## Review Questions

<details>
<summary><strong>1. What is an MCP Server?</strong></summary>

An MCP (Model Context Protocol) server is a programme that extends Claude's capabilities by providing it with tools. It acts as a bridge between Claude and external services or functionality, allowing Claude to perform actions beyond its built-in abilities (like sending emails, accessing databases, or interacting with APIs).

</details>

<details>
<summary><strong>2. What does "stdio" mean and why is it used for MCP communication?</strong></summary>

"stdio" stands for "standard input/output" - the basic text-based communication channels that every programme has (like reading from keyboard and writing to screen). MCP uses stdio because:
- It's simple and universal across all programming languages
- It's reliable and well-understood
- It allows the server to run as a subprocess of Claude Desktop
- No network configuration or ports are needed

</details>

<details>
<summary><strong>3. Do you think MCP servers always communicate via stdio?</strong></summary>

No, stdio is just one transport option. In fact, most MCP servers use HTTP/SSE (Server-Sent Events), even for local deployments. HTTP-based servers are particularly useful when you need:
- Connection to a remote MCP server
- Multiple clients to connect to the same server
- Web-based applications to access MCP tools
- Better debugging and monitoring capabilities

All remote MCP servers must use HTTP since stdio only works for local processes. The protocol is transport-agnostic, meaning the same MCP messages can be sent over different communication channels. We're using stdio here because it's the simplest option for a first MCP project with Claude Desktop.

</details>

<details>
<summary><strong>4. In the code, what does the <code>@server.list_tools()</code> decorator do?</strong></summary>

The `@server.list_tools()` decorator registers a function that tells Claude what tools are available. When Claude starts up, it calls this function to discover:
- The name of each tool
- A description of what the tool does
- What parameters (inputs) the tool requires
- What type each parameter should be

This allows Claude to understand what capabilities your server provides.

</details>

<details>
<summary><strong>5. What is the purpose of the <code>inputSchema</code> in the tool definition?</strong></summary>

The `inputSchema` defines the structure and requirements of the tool's parameters using JSON Schema format. It tells Claude:
- What parameters the tool accepts (like `to`, `subject`, `body`)
- What data type each parameter should be (string, number, boolean, etc.)
- Which parameters are required vs optional
- Descriptions to help Claude understand what each parameter is for

This allows Claude to call the tool correctly with properly formatted data.

</details>

<details>
<summary><strong>6. Why must the Python path in the config file point to the virtual environment's Python?</strong></summary>

The virtual environment's Python has access to the packages installed in that environment (like `mcp`). If you point to the system Python instead, it won't find the `mcp` package you installed in your virtual environment, resulting in a `ModuleNotFoundError`. The virtual environment's Python is located at `venv/bin/python` and knows to look in `venv/lib/` for packages.

</details>

<details>
<summary><strong>7. What happens when Claude wants to send an email? Trace the flow.</strong></summary>


1. **The user asks Claude to send an email** - For example: "Send an email to john@example.com saying hello"

2. **Claude analyses the request and decides to use the `send_email` tool** - The language model is prompted to output JSON in a specific format that the Claude application can parse. This JSON includes the tool name and parameters. If the model outputs malformed JSON or parameters that don't match the tool's `inputSchema`, Claude's application layer may perform schema validation and ask the model to correct itself before proceeding.

3. **Claude sends a tool call request via stdio** - This is sent as a JSON-RPC message over standard input/output to your MCP server, containing the tool name (`send_email`) and the extracted parameters (`to`, `subject`, `body`)

4. **Your server's `handle_call_tool()` function receives the request** - The MCP SDK automatically deserialises the JSON-RPC message and routes it to your decorated function

5. **The function extracts the parameters from the request** - It pulls out the `to`, `subject`, and `body` values from the `arguments` dictionary

6. **It calls the `send_email()` async function** - This awaits the actual email sending operation

7. **That function connects to Gmail's SMTP server and sends the email** - It authenticates using your credentials, establishes a secure TLS connection on port 587, and transmits the email via the SMTP protocol

8. **The function returns successfully** - Control returns back to `handle_call_tool()`

9. **Your server sends a success message back to Claude via stdio** - The response is serialised as JSON-RPC and written to standard output, which Claude Desktop is monitoring

10. **Claude tells the user the email was sent** - The language model incorporates the tool result into its response back to the user

</details>

