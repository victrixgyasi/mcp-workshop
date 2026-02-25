# MCP Workshop — Revision Notes

## Overview

This workshop covered three interconnected topics:

1. **Exercise 1** — Build a basic MCP server that gives Claude the ability to send emails
2. **Exercise 2** — Extend that server to read emails and use MCP sampling to generate AI draft replies
3. **Exercise 3** — Understand *how* LLMs reliably produce structured tool calls under the hood (fine-tuning + constrained decoding)

---

## What is MCP?

**Model Context Protocol (MCP)** is a standard that lets Claude (or any AI client) communicate with external programmes called **MCP servers**. These servers expose **tools** — functions the AI can call to interact with the outside world.

```
Claude Desktop / API
        │
        │  "I want to send an email"
        ▼
   MCP Client
        │
        │  JSON-RPC over stdio
        ▼
   MCP Server (your Python script)
        │
        │  calls Gmail SMTP
        ▼
   External Service
```

**Key idea:** MCP separates *what the AI can do* (tools) from *how it decides to use them* (the LLM). You can connect Claude to any service by writing a server.

---

## Exercise 1 — Basic MCP Server (`send_email`)

### What was built

An MCP server with a single `send_email` tool that sends emails via Gmail SMTP.

### Key files

- `mcp-servers/email/email_server.py` — the server
- `~/Library/Application Support/Claude/claude_desktop_config.json` — tells Claude Desktop where to find the server

### How an MCP server is structured

```python
from mcp.server import Server
import mcp.server.stdio
import mcp.types as types

server = Server("email-server")

# 1. Declare what tools exist
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="send_email",
            description="Send an email",
            inputSchema={
                "type": "object",
                "properties": {
                    "to":      {"type": "string"},
                    "subject": {"type": "string"},
                    "body":    {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        )
    ]

# 2. Handle tool calls
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "send_email":
        # ... send email via smtplib ...
        return [types.TextContent(type="text", text="✓ Email sent")]

# 3. Start the server (communicates via stdio)
async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         server.create_initialization_options())

asyncio.run(main())
```

### The two decorators

| Decorator | Purpose |
|-----------|---------|
| `@server.list_tools()` | Registers a function that tells the client what tools are available and their parameter schemas |
| `@server.call_tool()` | Registers a function that executes when the client calls a tool |

### `inputSchema`

This is a **JSON Schema** object that describes the tool's parameters. Claude uses it to:
- Know what arguments to pass
- Validate the structure of its own tool call before sending it

### Sending email with `smtplib`

```python
import smtplib
from email.mime.text import MIMEText

msg = MIMEText(body, "plain")
msg["From"] = email_user
msg["To"]   = recipient
msg["Subject"] = subject

with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
    smtp.starttls()                          # encrypt the connection
    smtp.login(email_user, app_password)
    smtp.send_message(msg)
```

**Why an App Password?** Gmail won't accept your regular password for SMTP. You generate a special 16-character App Password from your Google Account → Security → App Passwords.

### Claude Desktop config

```json
{
  "mcpServers": {
    "email": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/email_server.py"],
      "env": {
        "EMAIL_USER": "you@gmail.com",
        "EMAIL_APP_PASSWORD": "xxxx xxxx xxxx xxxx"
      }
    }
  }
}
```

Claude Desktop launches your script as a subprocess and communicates with it over **stdio** (standard input/output). This is why the Python path must point to the venv — that's where `mcp` is installed.

### Testing without Claude Desktop

Because Claude Desktop was unavailable, we tested using the Anthropic API directly with a Python script that:
1. Launches the MCP server as a subprocess
2. Uses `ClientSession` to connect and list tools
3. Calls the Anthropic API with the tools in Anthropic's format
4. Forwards any tool calls from Claude back to the MCP server

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import anthropic

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # Get tools from MCP and convert to Anthropic format
        tools_result = await session.list_tools()
        tools = [{"name": t.name, "description": t.description,
                  "input_schema": t.inputSchema} for t in tools_result.tools]

        # Call Anthropic API
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=tools,
            messages=[{"role": "user", "content": "Send an email..."}]
        )

        # When Claude calls a tool, forward it to the MCP server
        if response.stop_reason == "tool_use":
            for block in response.content:
                if block.type == "tool_use":
                    result = await session.call_tool(block.name, block.input)
```

### Communication flow

1. Claude Desktop starts your Python script
2. Claude asks "what tools do you have?" → your `list_tools()` responds
3. User asks Claude to send an email
4. Claude decides to call `send_email` with appropriate arguments
5. Claude sends a JSON-RPC `tools/call` message to your server via stdio
6. Your `call_tool()` handler runs, sends the email via SMTP
7. Your server returns a result to Claude
8. Claude tells the user the email was sent

---

## Exercise 2 — Email Assistant (`get_unread_emails` + `create_draft_reply`)

### What was built

Extended the email server with two new tools:
- `get_unread_emails` — reads unread emails via IMAP
- `create_draft_reply` — uses **MCP sampling** to generate a reply with Claude, then saves it as a Gmail draft

### Reading emails with `imaplib`

Exercise 1 used **SMTP** to *send* email. Exercise 2 uses **IMAP** to *read* email.

```python
import imaplib, email as email_lib
from email.header import decode_header

with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
    imap.login(email_user, email_password)
    imap.select("INBOX")

    # Search for unread messages
    _, message_ids = imap.search(None, "UNSEEN")
    ids = message_ids[0].split()

    for msg_id in ids:
        # Fetch the full RFC822 message
        _, msg_data = imap.fetch(msg_id, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw_email)

        # Decode subject (may be encoded, e.g. UTF-8 or base64)
        subject_parts = decode_header(msg["Subject"] or "")
        subject = ""
        for part, enc in subject_parts:
            if isinstance(part, bytes):
                subject += part.decode(enc or "utf-8", errors="replace")
            else:
                subject += part

        # Get plain text body (handle multipart emails)
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(...)
                    break
        else:
            body = msg.get_payload(decode=True).decode(...)
```

### Saving a draft to Gmail

To save to Gmail Drafts, use IMAP `append`:

```python
from email.mime.text import MIMEText
import imaplib, time

msg = MIMEText(draft_text, "plain")
msg["From"] = email_user
msg["To"]   = original_sender
msg["Subject"] = f"Re: {original_subject}"

with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
    imap.login(email_user, email_password)
    imap.append(
        "[Gmail]/Drafts",                          # Gmail's Drafts folder
        "\\Draft",                                 # IMAP flag
        imaplib.Time2Internaldate(time.time()),    # timestamp
        msg.as_bytes(),                            # raw message
    )
```

### MCP Sampling — the key new concept

**Sampling** is a mechanism where the **MCP server** asks the **client** (Claude Desktop) to run an LLM completion. This is the reverse of the normal flow.

```
Normal flow:      Client  →  Server  (client calls tools)
Sampling flow:    Server  →  Client  (server requests LLM completion)
```

**Why use sampling instead of calling the Anthropic API directly?**
- The server doesn't need its own API key
- The client's Claude instance handles the LLM call
- The server stays simple and stateless

```python
# Inside a tool handler on the server:
sampling_result = await server.request_context.session.create_message(
    messages=[
        types.SamplingMessage(
            role="user",
            content=types.TextContent(
                type="text",
                text=f"Please write a professional reply to:\n\n{email_body}"
            ),
        )
    ],
    max_tokens=1024,
)

draft_text = sampling_result.content.text
```

### Handling sampling in a test script (no Claude Desktop)

When testing via the Anthropic API directly, *our script* becomes the client. We need to handle sampling requests from the server ourselves:

```python
async def sampling_callback(context, params):
    """Called when the server sends a sampling request."""
    messages = [{"role": msg.role, "content": msg.content.text}
                for msg in params.messages]

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

# Pass the callback when creating the session:
async with ClientSession(read, write, sampling_callback=sampling_callback) as session:
    ...
```

### Summary of tools in Exercise 2

| Tool | Protocol | Direction |
|------|----------|-----------|
| `send_email` | SMTP (port 587, TLS) | Outbound |
| `get_unread_emails` | IMAP SSL (port 993) | Inbound |
| `create_draft_reply` | MCP sampling + IMAP | LLM → Draft |

---

## Exercise 3 — Tool Use From Scratch

### The problem

LLMs are trained on internet text. They've seen JSON, but a base model won't reliably produce *valid, structured* JSON when you ask it to make a tool call. It might:
- Add conversational text before/after the JSON
- Forget a comma or closing brace
- Hallucinate field names

### Solution 1: Fine-tuning

**Fine-tuning** trains the model on hundreds of examples of correct tool calls so it *wants* to produce the right format.

**Step 1 — Generate training data (`02_create_dataset.py`)**

500 synthetic examples pairing natural-language requests with correct JSON:

```json
{"prompt": "Send an email to bob@gmail.com about the project",
 "completion": "{\"tool\": \"send_email\", \"args\": {\"to\": \"bob@gmail.com\", \"subject\": \"the project\"}}"}

{"prompt": "What's the weather in Paris?",
 "completion": "{\"tool\": \"get_weather\", \"args\": {\"city\": \"Paris\"}}"}
```

**Step 2 — Fine-tune (`03_finetune.py`)**

Uses HuggingFace `Trainer` to run supervised fine-tuning (SFT) on `distilgpt2` (82M params):

```python
from transformers import AutoModelForCausalLM, Trainer, TrainingArguments

model = AutoModelForCausalLM.from_pretrained("distilgpt2")

# Format: "User request: {prompt}\nTool call JSON: {completion}"
training_texts = [f"User request: {ex['prompt']}\nTool call JSON: {ex['completion']}"
                  for ex in examples]

trainer = Trainer(
    model=model,
    args=TrainingArguments(num_train_epochs=3, learning_rate=5e-5, ...),
    train_dataset=dataset,
)
trainer.train()
```

**Result:** 0% → ~33% valid JSON. The model learned the *pattern* but it's still probabilistic — it can still make mistakes.

### Solution 2: Constrained Decoding

**Constrained decoding** makes it structurally *impossible* to output invalid JSON.

At every generation step, an LLM outputs a probability distribution over every token in its vocabulary (~50,000 tokens). Normally you sample from this. With constrained decoding, you **mask out invalid tokens** before sampling.

```
Generated so far: {"tool": "send_email", "args": {"to": "
Next valid tokens: only characters that can appear in an email address
Invalid tokens:    probability → 0
```

The from-scratch implementation in `05_constrained.py`:

```python
class SchemaConstrainedDecoder:
    def generate(self, prompt):
        input_ids = tokenizer.encode(prompt, return_tensors="pt")

        # 1. Force the JSON skeleton — the model doesn't choose these tokens
        input_ids = force_text(input_ids, '{"tool": "')

        # 2. Let the model pick a tool, but only from valid options
        logits = model(input_ids).logits[0, -1, :]
        tool_scores = {tool: logits[tokenizer.encode(tool)[0]] for tool in TOOLS}
        best_tool = max(tool_scores, key=tool_scores.get)

        # 3. Force the args structure for that tool
        input_ids = force_text(input_ids, f'{best_tool}", "args": {{')

        # 4. Force arg keys, let model generate values freely
        for arg in TOOL_ARGS[best_tool]:
            input_ids = force_text(input_ids, f'"{arg}": "')
            input_ids, value = generate_string_value(input_ids)  # stops at "
            ...

        return built_json  # always valid
```

**Result:** 100% valid, every time.

### Comparison

| Technique | What it does | Success rate | Limitation |
|-----------|-------------|--------------|------------|
| Base model | Nothing | 0% | No training signal |
| Fine-tuning | Makes model *want* valid JSON | ~33% | Still probabilistic |
| Constrained decoding | Makes invalid JSON *impossible* | 100% | Slower; needs schema known upfront |
| **Both together** | Industry standard | ~100% | — |

### What production systems do

| This workshop | OpenAI / Anthropic production |
|---------------|-------------------------------|
| 500 training examples | Millions of examples |
| distilgpt2 (82M params) | GPT-4 / Claude (100B+ params) |
| 3 tools | Hundreds of tools |
| Simple schema constraints | Sophisticated grammar engines |

The fundamentals are identical:
1. **SFT** (Supervised Fine-Tuning) — train on correct tool call examples
2. **Constrained decoding** — mechanically enforce valid output structure
3. **RLHF** (Reinforcement Learning from Human Feedback) — not covered here, but used to further improve quality

---

## Key Concepts Summary

### MCP transports

MCP is transport-agnostic. This workshop used **stdio** (simplest for local scripts), but production servers use **HTTP/SSE** for:
- Remote servers
- Multiple clients connecting to the same server
- Better debugging

### stdio vs HTTP

| stdio | HTTP/SSE |
|-------|----------|
| Local processes only | Local or remote |
| One client per server | Many clients |
| Simple, no config | Requires network setup |
| Used here | Used by most production MCP servers |

### Credentials best practice

- Never hardcode credentials in source code
- Pass secrets as **environment variables** (via the `env` block in `claude_desktop_config.json`, or `export` in shell)
- The `.gitignore` should exclude generated files (`venv/`, `data/`, `finetuned_model/`)

### Python email libraries

| Library | Protocol | Port | Use case |
|---------|----------|------|---------|
| `smtplib` | SMTP | 587 (TLS) | Sending email |
| `imaplib` | IMAP | 993 (SSL) | Reading email |
| `email.mime` | — | — | Constructing email messages |
| `email.header.decode_header` | — | — | Decoding encoded email subjects |

---

## Project Structure

```
fac-mcp/
├── README.md                    ← exercise instructions (different per branch)
│
├── mcp-servers/
│   └── email/
│       ├── email_server.py      ← the MCP server
│       ├── test_email.py        ← API-based test script
│       └── venv/                ← Python virtual environment
│
├── 01_baseline.py               ← exercise 3: base model test
├── 02_create_dataset.py         ← exercise 3: generate training data
├── 03_finetune.py               ← exercise 3: fine-tune distilgpt2
├── 04_inference.py              ← exercise 3: test fine-tuned model
├── 05_constrained.py            ← exercise 3: constrained decoding
├── requirements.txt             ← PyTorch, transformers, datasets
└── .gitignore                   ← excludes venv/, data/, finetuned_model/
```

---

## Quick Reference

### Run the email test script
```bash
export EMAIL_USER="you@gmail.com"
export EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
python3 mcp-servers/email/test_email.py
```

### Run exercise 3 scripts in order
```bash
source .venv/bin/activate
python 01_baseline.py       # 0% valid JSON
python 02_create_dataset.py # generate 500 training examples
python 03_finetune.py       # fine-tune (~2 mins on CPU)
python 04_inference.py      # ~33% valid JSON
python 05_constrained.py    # 100% valid JSON
```

### Check MCP server logs (macOS)
```bash
cat ~/Library/Logs/Claude/mcp-server-email.log
```

### Restart Claude Desktop
```bash
pkill -x "Claude" && sleep 2 && open -a "Claude"
```
