# 🤖 OmniBot — MCP-Native AI Agent Framework

> Plug any MCP server. Ship an agent in minutes. Not another chatbot template.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What is OmniBot?

OmniBot is a **lightweight AI agent framework** built around the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). Instead of hardcoding tool integrations, you declare MCP servers in a JSON config — OmniBot auto-discovers their tools and lets your agent use them.

Think of MCP as **USB-C for AI tools**. OmniBot is the laptop that accepts any USB-C device.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   User       │────▶│  Agent Loop   │────▶│  LLM (GPT/Claude)│
│  (Web/API)   │◀────│  (ReAct)      │◀────│  + Tool Calling   │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ MCP:     │ │ MCP:     │ │ Built-in:│
        │ filesystem│ │ fetch    │ │ RAG      │
        └──────────┘ └──────────┘ └──────────┘
```

## Why OmniBot?

| Feature | Dify/FastGPT | LangChain | **OmniBot** |
|---------|-------------|-----------|-------------|
| MCP native | ❌ | ❌ | ✅ First-class |
| Add tools | Code changes | Code changes | **JSON config** |
| Agent loop | Basic | Complex setup | **Built-in ReAct** |
| Weight | Heavy platform | Heavy deps | **Lightweight** |
| Deploy | Complex | Library only | **Docker one-click** |

## Quick Start

### 1. Install & Run

```bash
git clone https://github.com/coldxiangyu163/omnibot.git
cd omnibot
cp .env.example .env          # Add your API keys
pip install -r requirements.txt
make dev                       # http://localhost:8000
```

### 2. Add MCP Tools (Zero Code)

Create `omnibot.json` in the project root:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx" }
    }
  }
}
```

Restart OmniBot. That's it — your agent can now read files, fetch URLs, and interact with GitHub. **No code changes.**

### 3. Talk to Your Agent

```bash
# Simple chat
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "List all files in the data directory"}'

# Full agent mode with step details
curl -X POST http://localhost:8000/api/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Fetch https://news.ycombinator.com and summarize the top 3 stories"}'

# See all available tools
curl http://localhost:8000/api/v1/tools
```

## How It Works

OmniBot uses a **ReAct (Reason + Act) agent loop**:

```
User: "What's in my docs folder?"
  │
  ▼
Agent Step 1:
  LLM thinks: "I should use the filesystem tool to list the directory"
  Tool call:  filesystem.list_directory(path="./docs")
  Result:     ["report.pdf", "notes.md", "data.csv"]
  │
  ▼
Agent Step 2:
  LLM thinks: "I have the file list, let me respond"
  Response:   "Your docs folder contains 3 files: report.pdf, notes.md, and data.csv"
```

The agent keeps looping (up to `MAX_AGENT_ITERATIONS`) until it has enough info to respond.

## Register Custom Python Tools

Don't want to run an MCP server? Register Python functions directly:

```python
from app.core.engine import engine

async def get_weather(city: str) -> str:
    return f"Weather in {city}: 22°C, sunny"

engine.registry.register_builtin(
    name="get_weather",
    description="Get current weather for a city",
    input_schema={
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
    handler=get_weather,
)
```

## Knowledge Base (RAG)

RAG is a **built-in tool** — the agent decides when to search your docs:

```bash
# Upload documents
curl -X POST http://localhost:8000/api/v1/knowledge \
  -F "file=@company-faq.pdf"

# The agent will automatically search when relevant
curl -X POST http://localhost:8000/api/v1/chat \
  -d '{"text": "What is our refund policy?"}'
```

## Project Structure

```
omnibot/
├── app/
│   ├── main.py              # FastAPI entry + lifespan
│   ├── config.py            # Settings
│   ├── core/
│   │   ├── engine.py        # AgentEngine (orchestrator)
│   │   ├── agent/loop.py    # ReAct agent loop
│   │   ├── mcp/
│   │   │   ├── client.py    # MCP stdio client
│   │   │   └── registry.py  # Unified tool registry
│   │   ├── llm/             # LLM providers (OpenAI, Anthropic)
│   │   └── rag/             # RAG pipeline (built-in tool)
│   ├── api/v1/              # REST API
│   ├── channels/            # WebSocket, future: Slack/Telegram
│   └── schemas/             # Pydantic models
├── examples/                # Quickstart, MCP tools, custom agent
├── omnibot.example.json     # MCP server config template
├── static/widget/           # Embeddable web chat widget
└── tests/
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | `openai` or `anthropic` | `openai` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `MAX_AGENT_ITERATIONS` | Max tool-calling rounds | `10` |
| `MCP_CONFIG_PATH` | Path to MCP config | `omnibot.json` |

## Run with Docker

```bash
cp .env.example .env
cp omnibot.example.json omnibot.json
docker compose up -d
```

## Roadmap

- [x] MCP client (stdio transport)
- [x] ReAct agent loop with tool calling
- [x] OpenAI + Anthropic function calling
- [x] Unified tool registry (MCP + built-in)
- [x] RAG as built-in agent tool
- [x] REST API + WebSocket
- [x] Web chat widget
- [ ] MCP SSE transport
- [ ] Streaming responses
- [ ] Conversation memory (multi-turn)
- [ ] Slack / Telegram / Lark channels
- [ ] Agent-to-agent delegation
- [ ] MCP server mode (expose OmniBot as MCP server)

## Compatible MCP Servers

Any MCP server works. Here are some popular ones:

| Server | What it does |
|--------|-------------|
| `@modelcontextprotocol/server-filesystem` | Read/write local files |
| `mcp-server-fetch` | Fetch and parse web pages |
| `@modelcontextprotocol/server-github` | GitHub API |
| `@modelcontextprotocol/server-postgres` | Query PostgreSQL |
| `@playwright/mcp` | Browser automation |
| `mcp-server-sqlite` | SQLite database |

Browse more at [MCP Servers Directory](https://github.com/modelcontextprotocol/servers).

## License

MIT — Use it, modify it, ship it, make money with it.
