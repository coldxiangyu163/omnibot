"""OmniBot — MCP-native AI Agent Framework."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.api.v1 import chat, knowledge, tools, agents
from app.channels.web import router as web_router
from app.core.engine import engine
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize agent engine + MCP servers
    await engine.initialize(settings.mcp_config_path)
    yield
    # Shutdown: clean up MCP server processes
    await engine.shutdown()


app = FastAPI(
    title="OmniBot",
    description="MCP-native AI Agent Framework — plug any MCP server, ship an agent in minutes.",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(chat.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(tools.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(web_router)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the chat UI."""
    index_path = Path("static/index.html")
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    # Fallback to JSON info if no UI file
    tool_count = len(engine.registry.tool_names) if engine._initialized else 0
    return HTMLResponse(content=f"<h1>OmniBot v0.2.0</h1><p>Tools loaded: {tool_count}</p>")


@app.get("/api/info")
async def info():
    """API info endpoint (moved from /)."""
    tool_count = len(engine.registry.tool_names) if engine._initialized else 0
    return {
        "name": "OmniBot",
        "version": "0.2.0",
        "tagline": "MCP-native AI Agent Framework",
        "status": "running",
        "tools_loaded": tool_count,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "engine_ready": engine._initialized}
