"""Tools management API."""
from fastapi import APIRouter
from app.core.engine import engine
from app.schemas.tool import ToolInfo

router = APIRouter(tags=["tools"])


@router.get("/tools", response_model=list[ToolInfo])
async def list_tools():
    """List all available tools (MCP + built-in)."""
    if not engine._initialized:
        await engine.initialize()

    tools = []
    for name, t in engine.registry._mcp_tools.items():
        tools.append(ToolInfo(
            name=name, description=t.description,
            source=f"mcp:{t.server_name}", input_schema=t.input_schema,
        ))
    for name, t in engine.registry._builtin_tools.items():
        tools.append(ToolInfo(
            name=name, description=t.description,
            source="builtin", input_schema=t.input_schema,
        ))
    return tools
