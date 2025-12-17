# Building a Simple Email MCP Server for Claude Desktop (JavaScript)

This guide will walk you through creating a Model Context Protocol (MCP) server that allows Claude Desktop to send emails on your behalf. The aim here is to build a sense of what MCP can do for us and some boilerplate to get us started.

## What You'll Build

An MCP server is a programme that extends Claude's capabilities by giving it access to tools. In this case, we're building a server that provides Claude with a `send_email` tool, allowing it to send emails through Gmail.

## Prerequisites

- **Claude Desktop** installed on your computer
- **Node.js 18 or higher** installed
- A **Gmail account** (we'll use Gmail's SMTP server)

## Step 1: Set Up Your Project Directory

First, create a dedicated folder for your MCP server:

```bash
mkdir -p ~/mcp-servers/email
cd ~/mcp-servers/email
```

## Step 2: Initialize Your Node.js Project

Create a new Node.js project with npm:

```bash
npm init -y
```

This creates a `package.json` file that will track your project's dependencies.

## Step 3: Install Required Dependencies

Install the MCP SDK and nodemailer (for sending emails):

```bash
npm install @modelcontextprotocol/sdk nodemailer
```

This installs:
- `@modelcontextprotocol/sdk` - The Model Context Protocol library
- `nodemailer` - A popular Node.js library for sending emails

## Step 4: Create the Server Code

Create a file called `email_server.js` in your project directory and paste the following code:

```javascript
#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import nodemailer from "nodemailer";

const server = new Server(
  {
    name: "email-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "send_email",
        description: "Send an email",
        inputSchema: {
          type: "object",
          properties: {
            to: {
              type: "string",
              description: "Recipient email address",
            },
            subject: {
              type: "string",
              description: "Email subject",
            },
            body: {
              type: "string",
              description: "Email body content",
            },
          },
          required: ["to", "subject", "body"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name !== "send_email") {
    throw new Error(`Unknown tool: ${request.params.name}`);
  }

  const { to, subject, body } = request.params.arguments;

  const transporter = nodemailer.createTransport({
    service: "gmail",
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_APP_PASSWORD,
    },
  });

  // Send email
  await transporter.sendMail({
    from: process.env.EMAIL_USER,
    to: to,
    subject: subject,
    text: body,
  });

  return {
    content: [
      {
        type: "text",
        text: `✓ Email sent to ${to}`,
      },
    ],
  };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Email MCP server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
```

### Update package.json

Add `"type": "module"` to your `package.json` to enable ES modules:

```json
{
  "name": "email",
  "version": "1.0.0",
  "type": "module",
  "main": "email_server.js",
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0",
    "nodemailer": "^6.9.7"
  }
}
```

### Understanding the Code

- **`nodemailer.createTransport()`**: Creates an SMTP transporter configured for Gmail
- **`server.setRequestHandler(ListToolsRequestSchema, ...)`**: Tells Claude what tools are available and what parameters they need
- **`server.setRequestHandler(CallToolRequestSchema, ...)`**: Handles the actual execution when Claude decides to use a tool
- **`main()`**: Sets up the communication channel between your server and Claude Desktop using stdio

## Step 5: Set Up Gmail App Password

For security reasons, Gmail requires an "App Password" rather than your regular password:

1. Go to your Google Account settings at [myaccount.google.com](https://myaccount.google.com)
2. Navigate to **Security** in the left sidebar
3. Enable **2-Step Verification** if you haven't already (this is required for App Passwords)
4. Once 2FA is enabled, go back to **Security**
5. Scroll down to "How you sign in to Google"
6. Click on **App passwords** (or search for "App passwords" in settings)
   - If you struggle to find it, you can go directly to: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

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
      "command": "node",
      "args": ["/full/path/to/your/email_server.js"],
      "env": {
        "EMAIL_USER": "your-email@gmail.com",
        "EMAIL_APP_PASSWORD": "your-16-char-app-password"
      }
    }
  }
}
```

### Get Your Full Path

To find the exact path you need for the script:

**macOS/Linux:**
```bash
cd ~/mcp-servers/email
pwd
```

**Windows (PowerShell):**
```powershell
cd ~\mcp-servers\email
(Get-Location).Path
```

This will show your current directory. Then append `/email_server.js` (or `\email_server.js` on Windows) to it.

### Example Configuration

Here's what a complete config might look like:

**macOS/Linux:**
```json
{
  "mcpServers": {
    "email": {
      "command": "node",
      "args": ["/Users/izaak/mcp-servers/email/email_server.js"],
      "env": {
        "EMAIL_USER": "izaak@example.com",
        "EMAIL_APP_PASSWORD": "abcd efgh ijkl mnop"
      }
    }
  }
}
```

**Important notes:**
- Replace the path with your actual full path
- Replace the email with your Gmail address
- Replace the app password with the one you generated (remove spaces)
- Use forward slashes (`/`) even on Windows in the JSON file
- Make sure there are no trailing commas in your JSON

## Step 7: Make the Script Executable (macOS/Linux only)

On macOS and Linux, make your script executable:

```bash
chmod +x email_server.js
```

This step is not needed on Windows.

## Step 8: Restart Claude Desktop

Quit Claude Desktop completely (don't just close the window - actually quit the application) and then reopen it.

## Step 9: Test Your Server

Open a new conversation in Claude Desktop and try:

```
Send an email to [YOUR EMAIL] with the subject "Test from MCP" and body "This is a test email sent through Claude!"
```

If everything is set up correctly, you should see Claude use the `send_email` tool and confirm that the email was sent.

## Troubleshooting

### "Cannot find module '@modelcontextprotocol/sdk'"

This means the MCP library isn't installed. Make sure:
1. You're in the correct directory (`~/mcp-servers/email`)
2. You ran `npm install @modelcontextprotocol/sdk nodemailer`
3. The `node_modules` folder exists in your project directory

### "Can't open file" or "Cannot find module"

The path in your config file is incorrect. Double-check:
1. The file `email_server.js` actually exists at that location
2. You're using the full absolute path (starting with `/` on macOS/Linux or `C:\` on Windows)
3. There are no typos in the path
4. If on Windows, try double backslashes (`\\`)

### "Authentication failed" or "SMTP error"

Your Gmail credentials might be incorrect. Verify:
1. You're using your Gmail address (not another email service)
2. You're using the App Password, not your regular Gmail password
3. The App Password has no spaces (should be 16 characters altogether)
4. 2-Factor Authentication is enabled on your Google account

### Claude Desktop doesn't seem to have access to the MCP server

If Claude Desktop doesn't appear to recognize your MCP server:

1. **Check the MCP Server Panel in Claude Desktop**
   - Look in the MCP server indicator panel to see if your server appears there

2. **Verify the configuration in Claude Desktop settings**
   - Open Claude Desktop
   - Go to the **Settings panel** → **User** → **Settings** → **Developer** → **Edit config**
   - This shows all your configured MCP servers and displays any errors that might be occurring

3. **Common issues to check**
   - Make sure your config file is valid JSON (no trailing commas, all quotes properly closed)
   - Verify the paths are absolute and correct
   - Check that the script file actually exists at that path
   - Ensure Node.js is installed and accessible (run `node --version` in terminal)
   - Look for any error messages displayed in the config editor

### Check the Logs

Claude Desktop keeps logs that can help diagnose issues:

**macOS:**
```
~/Library/Logs/Claude/mcp*.log
```

Look for recent log files and check for error messages.

## How It Works

1. **Claude Desktop starts your server**: When Claude launches, it runs your Node.js script as a subprocess
2. **Communication via stdio**: Your server and Claude communicate through standard input/output
3. **Tool discovery**: Claude asks your server what tools it has available (via `ListToolsRequest`)
4. **Tool execution**: When Claude wants to send an email, it calls your `send_email` tool with the appropriate parameters
5. **Results return**: Your server sends the email and reports back success or failure

## Key Concepts Recap

- **MCP Server**: A programme that provides tools to Claude
- **Tools**: Functions that Claude can call (like `send_email`)
- **Nodemailer**: A Node.js library that simplifies sending emails via SMTP

You've now built your first MCP server and extended Claude's capabilities. This same pattern can be used to connect any AI application to databases, APIs, file systems, and much more.

## Quiz Questions

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
<summary><strong>4. In the code, what does the <code>ListToolsRequestSchema</code> handler do?</strong></summary>

The `ListToolsRequestSchema` handler registers a function that tells Claude what tools are available. When Claude starts up, it calls this handler to discover:
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
<summary><strong>6. Why do we use <code>"type": "module"</code> in package.json?</strong></summary>

Setting `"type": "module"` in `package.json` tells Node.js to treat `.js` files as ES modules rather than CommonJS modules. This allows us to use modern JavaScript features like:
- `import` and `export` statements instead of `require()` and `module.exports`
- Top-level `await`
- Better tree-shaking and optimization

The MCP SDK uses ES modules, so we need to configure our project to support them.

</details>

<details>
<summary><strong>7. What happens when Claude wants to send an email? Trace the flow.</strong></summary>

1. **The user asks Claude to send an email** - For example: "Send an email to john@example.com saying hello"

2. **Claude analyses the request and decides to use the `send_email` tool** - The language model is prompted to output JSON in a specific format that the Claude application can parse. This JSON includes the tool name and parameters. If the model outputs malformed JSON or parameters that don't match the tool's `inputSchema`, Claude's application layer may perform schema validation and ask the model to correct itself before proceeding.

3. **Claude sends a tool call request via stdio** - This is sent as a JSON-RPC message over standard input/output to your MCP server, containing the tool name (`send_email`) and the extracted parameters (`to`, `subject`, `body`)

4. **Your server's `CallToolRequestSchema` handler receives the request** - The MCP SDK automatically deserializes the JSON-RPC message and routes it to your registered handler

5. **The handler extracts the parameters from the request** - It pulls out the `to`, `subject`, and `body` values from `request.params.arguments`

6. **It creates a nodemailer transporter** - This configures the connection to Gmail's SMTP server with your credentials

7. **The handler calls `transporter.sendMail()`** - This sends the email via SMTP, authenticating with your App Password, establishing a secure connection, and transmitting the message

8. **The function returns successfully** - A success response is created with the result message

9. **Your server sends a success message back to Claude via stdio** - The response is serialized as JSON-RPC and written to standard output, which Claude Desktop is monitoring

10. **Claude tells the user the email was sent** - The language model incorporates the tool result into its response back to the user

</details>

## Exercise

https://izaakrogan.github.io/mcp-exercise/
