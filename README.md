<p align="center">
  <img src="https://raw.githubusercontent.com/coldxiangyu163/omnibot/main/static/widget/logo.png" alt="OmniBot Logo" width="120" />
</p>

<h1 align="center">🤖 OmniBot</h1>

<p align="center">
  <strong>MCP-native AI Agent Framework — plug any MCP server, ship an agent in minutes.</strong>
</p>

<p align="center">
  <a href="https://github.com/coldxiangyu163/omnibot/stargazers"><img src="https://img.shields.io/github/stars/coldxiangyu163/omnibot?style=flat-square&color=yellow" alt="Stars" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square" alt="Python 3.11+" /></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0.115+-green.svg?style=flat-square" alt="FastAPI" /></a>
  <a href="https://github.com/coldxiangyu163/omnibot/issues"><img src="https://img.shields.io/github/issues/coldxiangyu163/omnibot?style=flat-square" alt="Issues" /></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#core-features">Features</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#comparison">Comparison</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## What is OmniBot?

OmniBot is a **lightweight AI agent framework** built around the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). Instead of hardcoding tool integrations, you declare MCP servers in a JSON config — OmniBot auto-discovers their tools and lets your agent use them with zero code changes.

> Think of MCP as **USB-C for AI tools**. OmniBot is the laptop that accepts any USB-C device.

---

## Architecture

```
                          ┌──────────────────────────────────────────────┐
                          │                  OmniBot                     │
                          │                                              │
┌──────────┐   REST/WS    │  ┌────────────┐    ┌──────────────────────┐  │
│  Web UI  │─────────────▶│  │  FastAPI    │───▶│   Agent Engine       │  │
│  (Chat   │◀─────────────│  │  Gateway    │◀───│                      │  │
│  Widget) │              │  └────────────┘    │  ┌────────────────┐  │  │
└──────────┘              │                    │  │  ReAct Loop    │  │  │
                          │                    │  │  ┌──────────┐  │  │  │
┌──────────┐              │                    │  │  │ Reason   │  │  │  │
│  cURL /  │──────────────│                    │  │  │    ↓     │  │  │  │
│  API     │              │                    │  │  │ Act      │  │  │  │
│  Client  │              │                    │  │  │    ↓     │  │  │  │
└──────────┘              │                    │  │  │ Observe  │  │  │  │
                          │                    │  │  └──────────┘  │  │  │
                          │                    │  └────────────────┘  │  │
                          │                    └──────────┬───────────┘  │
                          │                               │              │
                          │              ┌────────────────┼──────────┐  │
                          │              │   Unified Tool Registry    │  │
                          │              └──┬─────────┬──────────┬───┘  │
                          │                 │         │          │      │
                          └─────────────────┼─────────┼──────────┼──────┘
                                            │         │          │
                          ┌─────────────────┼─────────┼──────────┼──────┐
                          │   MCP Servers   │         │          │      │
                          │                 ▼         ▼          ▼      │
                          │  ┌───────────┐ ┌────────┐ ┌──────────────┐ │
                          │  │filesystem │ │ fetch  │ │   github     │ │
                          │  └───────────┘ └────────┘ └──────────────┘ │
                          │  ┌───────────┐ ┌────────┐ ┌──────────────┐ │
                          │  │ postgres  │ │sqlite  │ │  playwright  │ │
                          │  └───────────┘ └────────┘ └──────────────┘ │
                          └─────────────────────────────────────────────┘

                          ┌─────────────────────────────────────────────┐
                          │   LLM Providers                             │
                          │   ┌──────────┐  ┌───────────┐  ┌────────┐  │
                          │   │  OpenAI  │  │ Anthropic │  │ More.. │  │
                          │   │ GPT-4o   │  │  Claude   │  │        │  │
                          │   └──────────┘  └───────────┘  └────────┘  │
                          └─────────────────────────────────────────────┘
```

---

## Core Features

### 🔌 MCP Client (First-Class)

OmniBot speaks MCP natively. Declare any MCP-compatible server in `omnibot.json` and it's instantly available as an agent tool — no code, no adapters, no glue.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
    }
  }
}
```

### 🧠 ReAct Agent Loop

A built-in **Reason → Act → Observe** loop drives the agent. The LLM decides which tools to call, interprets results, and keeps iterating until it has a complete answer — up to `MAX_AGENT_ITERATIONS` rounds.

### 🗂️ Unified Tool Registry

MCP tools and native Python tools live side-by-side in one registry. The agent doesn't care where a tool comes from — it just picks the right one.

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

### 🤖 Multi-LLM Support

Switch between LLM providers with a single env variable. Currently supports:

| Provider | Models | Function Calling |
|----------|--------|-----------------|
| OpenAI | GPT-4o, GPT-4o-mini, o1, etc. | ✅ |
| Anthropic | Claude 3.5 Sonnet, Claude 3 Opus, etc. | ✅ |

### 📚 RAG (Built-in Agent Tool)

RAG isn't a separate pipeline — it's a tool the agent can invoke when it needs to search your knowledge base. Upload documents, and the agent decides when to query them.

```bash
# Upload a document
curl -X POST http://localhost:8000/api/v1/knowledge \
  -F "file=@company-faq.pdf"

# Agent auto-searches when relevant
curl -X POST http://localhost:8000/api/v1/chat \
  -d '{"text": "What is our refund policy?"}'
```

---

## Quick Start

Get OmniBot running in 3 steps:

### Step 1: Clone & Install

```bash
git clone https://github.com/coldxiangyu163/omnibot.git
cd omnibot
cp .env.example .env          # Add your API keys
pip install -r requirements.txt
```

### Step 2: Configure MCP Tools

Create `omnibot.json` in the project root (or copy from the template):

```bash
cp omnibot.example.json omnibot.json
```

Edit it to declare the MCP servers you want:

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

### Step 3: Run

```bash
# Development
make dev                       # → http://localhost:8000

# Or with Docker
docker compose up -d           # → http://localhost:8000
```

That's it. Your agent is live with all declared MCP tools auto-discovered and ready.

### Try It Out

```bash
# Simple chat
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "List all files in the data directory"}'

# Full agent mode with step-by-step details
curl -X POST http://localhost:8000/api/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Fetch https://news.ycombinator.com and summarize the top 3 stories"}'

# List all available tools (MCP + built-in)
curl http://localhost:8000/api/v1/tools
```

---

## How It Works

OmniBot uses a **ReAct (Reason + Act) agent loop**:

```
User: "What's in my docs folder?"
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ Agent Step 1                                        │
│   Think:  "I should list the directory"             │
│   Act:    filesystem.list_directory(path="./docs")  │
│   Result: ["report.pdf", "notes.md", "data.csv"]   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ Agent Step 2                                        │
│   Think:  "I have the file list, I can respond"     │
│   Response: "Your docs folder contains 3 files:     │
│              report.pdf, notes.md, and data.csv"    │
└─────────────────────────────────────────────────────┘
```

The agent keeps looping (up to `MAX_AGENT_ITERATIONS`) until it has enough information to give a final answer.

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM backend: `openai` or `anthropic` | `openai` |
| `LLM_MODEL` | Model name (e.g. `gpt-4o`, `claude-3-5-sonnet-20241022`) | `gpt-4o` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `MAX_AGENT_ITERATIONS` | Max tool-calling rounds per request | `10` |
| `MCP_CONFIG_PATH` | Path to MCP server config file | `omnibot.json` |

### MCP Server Config (`omnibot.json`)

Each entry under `mcpServers` defines a tool provider:

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "<executable>",
      "args": ["<arg1>", "<arg2>"],
      "env": {
        "<ENV_VAR>": "<value>"
      }
    }
  }
}
```

OmniBot connects to each server via stdio, discovers its tools, and registers them in the unified tool registry on startup.

---

## Comparison

<a id="comparison"></a>

| Feature | LangChain | CrewAI | AutoGen | Dify / FastGPT | **OmniBot** |
|---------|-----------|--------|---------|-----------------|-------------|
| MCP native | ❌ Adapter needed | ❌ | ❌ | ❌ | ✅ First-class |
| Add new tools | Write Python code | Write Python code | Write Python code | Platform UI | **JSON config** |
| Agent loop | Manual chain setup | Role-based | Conversation-based | Basic flow | **Built-in ReAct** |
| Multi-LLM | ✅ | ✅ | ✅ | ✅ | ✅ |
| RAG | Separate chain | Plugin | Plugin | Built-in | **Built-in tool** |
| Dependency weight | Heavy (~50+ deps) | Medium | Medium | Full platform | **Lightweight** |
| Learning curve | Steep | Moderate | Moderate | Low (no-code) | **Low** |
| Deployment | Library (DIY) | Library (DIY) | Library (DIY) | Docker (heavy) | **Docker one-click** |
| Best for | Complex pipelines | Multi-agent teams | Multi-agent chat | No-code users | **MCP-first agents** |

**OmniBot's sweet spot**: You want a production-ready agent that can use any MCP tool with minimal setup, without pulling in a massive framework.

---

## Project Structure

```
omnibot/
├── app/
│   ├── main.py                # FastAPI entry point + lifespan
│   ├── config.py              # Settings & env loading
│   ├── core/
│   │   ├── engine.py          # AgentEngine — the orchestrator
│   │   ├── agent/
│   │   │   └── loop.py        # ReAct agent loop implementation
│   │   ├── mcp/
│   │   │   ├── client.py      # MCP stdio client
│   │   │   └── registry.py    # Unified tool registry (MCP + built-in)
│   │   ├── llm/               # LLM providers (OpenAI, Anthropic)
│   │   └── rag/               # RAG pipeline (vector search tool)
│   ├── api/v1/                # REST API routes
│   ├── channels/              # WebSocket, future: Slack / Telegram
│   └── schemas/               # Pydantic request/response models
├── examples/                  # Quickstart & usage examples
├── static/widget/             # Embeddable web chat widget
├── omnibot.example.json       # MCP config template
├── docker-compose.yml         # One-click Docker deployment
├── Makefile                   # Dev commands
├── requirements.txt           # Python dependencies
└── tests/                     # Test suite
```

---

## Compatible MCP Servers

Any MCP-compatible server works out of the box. Popular choices:

| Server | What It Does | Install |
|--------|-------------|---------|
| `@modelcontextprotocol/server-filesystem` | Read/write local files | `npx -y @modelcontextprotocol/server-filesystem` |
| `mcp-server-fetch` | Fetch & parse web pages | `uvx mcp-server-fetch` |
| `@modelcontextprotocol/server-github` | GitHub API (repos, issues, PRs) | `npx -y @modelcontextprotocol/server-github` |
| `@modelcontextprotocol/server-postgres` | Query PostgreSQL databases | `npx -y @modelcontextprotocol/server-postgres` |
| `@playwright/mcp` | Browser automation | `npx -y @playwright/mcp` |
| `mcp-server-sqlite` | SQLite database operations | `uvx mcp-server-sqlite` |

Browse the full directory at [MCP Servers](https://github.com/modelcontextprotocol/servers).

---

## Roadmap

- [x] MCP client (stdio transport)
- [x] ReAct agent loop with tool calling
- [x] OpenAI + Anthropic function calling
- [x] Unified tool registry (MCP + built-in)
- [x] RAG as built-in agent tool
- [x] REST API + WebSocket
- [x] Embeddable web chat widget
- [ ] MCP SSE / Streamable HTTP transport
- [ ] Streaming responses (SSE)
- [ ] Conversation memory (multi-turn context)
- [ ] Channel integrations (Slack / Telegram / Lark)
- [ ] Agent-to-agent delegation
- [ ] MCP server mode (expose OmniBot itself as an MCP server)

---

## Contributing

Contributions are welcome! Here's how to get started:

### Development Setup

```bash
git clone https://github.com/coldxiangyu163/omnibot.git
cd omnibot
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
make dev
```

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feat/my-feature`
3. **Commit** your changes: `git commit -m "feat: add my feature"`
4. **Push** to your fork: `git push origin feat/my-feature`
5. **Open** a Pull Request against `main`

### Guidelines

- Follow existing code style and project structure
- Add tests for new features when possible
- Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages
- Keep PRs focused — one feature or fix per PR
- Update documentation if your change affects the public API

### Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/coldxiangyu163/omnibot/issues/new) with:
- A clear description of the problem or suggestion
- Steps to reproduce (for bugs)
- Expected vs actual behavior

---

## License

[MIT](LICENSE) — Use it, modify it, ship it, make money with it.

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/coldxiangyu163">coldxiangyu</a></sub>
</p>

