# 🤖 OmniBot — AI-Powered Multi-Channel Chatbot Framework

> Production-ready chatbot template with RAG knowledge base, appointment booking, and multi-channel support. Deploy your AI assistant in minutes, not weeks.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Why OmniBot?

Most chatbot demos are toys. OmniBot is built for real business use cases:

- 🔌 **Multi-Channel** — One bot, everywhere. Web widget, Slack, WhatsApp, Telegram, Lark.
- 🧠 **RAG Knowledge Base** — Upload your docs (PDF, Markdown, TXT). Your bot answers from YOUR data.
- 📅 **Appointment Booking** — Built-in scheduling with Google Calendar integration.
- 🌍 **Multilingual** — Auto-detects language and responds accordingly.
- 🔧 **MCP Protocol** — Expose bot capabilities as standardized tools for AI agent orchestration.
- 🚀 **Deploy in Minutes** — Docker Compose up and running.

## 🏗️ Architecture

```
User Message → Channel Adapter → Unified BotMessage → RAG Retrieval → LLM → Response
```

Supported LLM providers: OpenAI (GPT-4o) and Anthropic (Claude), switchable via config.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI or Anthropic API key

### Run Locally

```bash
git clone https://github.com/coldxiangyu163/omnibot.git
cd omnibot
cp .env.example .env          # Add your API keys
pip install -r requirements.txt
make dev                       # Visit http://localhost:8000
```

### Run with Docker

```bash
cp .env.example .env
docker compose up -d
```

## 📁 Project Structure

```
omnibot/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings (pydantic-settings)
│   ├── core/
│   │   ├── engine.py        # Bot orchestrator (RAG + LLM)
│   │   ├── llm/             # LLM providers (OpenAI, Anthropic)
│   │   └── rag/             # RAG pipeline (ChromaDB)
│   ├── api/v1/              # REST API routes
│   ├── channels/            # Channel adapters (web, slack, etc.)
│   └── schemas/             # Pydantic models
├── static/widget/           # Embeddable web chat widget
├── tests/                   # pytest test suite
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🔌 Web Widget

Embed the chat widget on any website:

```html
<script src="https://your-domain.com/static/widget/widget.js"></script>
```

## 🧠 Knowledge Base (RAG)

Upload documents via API:

```bash
curl -X POST http://localhost:8000/api/v1/knowledge \
  -F "file=@company-faq.pdf"
```

Check stats:

```bash
curl http://localhost:8000/api/v1/knowledge/stats
```

## 💬 Chat API

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "What are your business hours?"}'
```

## 🛠️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | `openai` or `anthropic` | `openai` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `CHROMA_PERSIST_DIR` | Vector DB storage | `./data/chroma` |

## 🧪 Testing

```bash
pip install -e ".[dev]"
make test
```

## 🗺️ Roadmap

- [x] FastAPI + OpenAI/Anthropic LLM providers
- [x] RAG pipeline with ChromaDB
- [x] Web Widget (WebSocket)
- [x] REST API for chat & knowledge
- [ ] Slack integration
- [ ] Telegram integration
- [ ] Lark (飞书) integration
- [ ] Appointment booking + Google Calendar
- [ ] Admin dashboard
- [ ] MCP Protocol server

## 🤝 Hire Me

I build production AI chatbots and automation systems for businesses.

- 🌐 Multi-channel deployment (Web, Slack, WhatsApp, Telegram, Lark)
- 🧠 Custom RAG pipelines for your specific domain
- 🔄 CRM/ERP integration & workflow automation
- 📈 Analytics and continuous optimization

**Let's talk** → [GitHub](https://github.com/coldxiangyu163)

## 📄 License

MIT — Use it for your business, modify it, make money with it.
