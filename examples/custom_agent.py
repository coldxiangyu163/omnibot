"""
Custom Agent Example — register your own Python tools alongside MCP tools.

This shows how to mix built-in Python functions with MCP server tools.
"""
import asyncio
import json
from datetime import datetime
from app.core.engine import AgentEngine


async def get_current_time(timezone: str = "UTC") -> str:
    """Get the current time."""
    now = datetime.now()
    return json.dumps({"time": now.isoformat(), "timezone": timezone})


async def calculate(expression: str) -> str:
    """Evaluate a math expression safely."""
    try:
        # Only allow safe math operations
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return json.dumps({"error": "Invalid characters in expression"})
        result = eval(expression)  # safe subset only
        return json.dumps({"expression": expression, "result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def main():
    engine = AgentEngine()
    await engine.initialize()

    # Register custom Python tools
    engine.registry.register_builtin(
        name="get_current_time",
        description="Get the current date and time",
        input_schema={
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "Timezone name", "default": "UTC"},
            },
        },
        handler=get_current_time,
    )

    engine.registry.register_builtin(
        name="calculate",
        description="Evaluate a mathematical expression",
        input_schema={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"},
            },
            "required": ["expression"],
        },
        handler=calculate,
    )

    print(f"Tools: {engine.registry.tool_names}")

    result = await engine.run_agent(
        "What time is it now? Also, what is 1234 * 5678?"
    )
    print(f"\n{result.response}")
    print(f"\n({result.total_tool_calls} tool calls in {result.total_duration_ms}ms)")

    await engine.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
