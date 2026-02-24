"""
OmniBot Quickstart — minimal agent in 10 lines.

Usage:
    pip install omnibot
    export OPENAI_API_KEY=sk-...
    python examples/quickstart.py
"""
import asyncio
from app.core.engine import AgentEngine


async def main():
    engine = AgentEngine()
    await engine.initialize()

    result = await engine.run_agent("What is 2 + 2? Explain step by step.")
    print(f"Response: {result.response}")
    print(f"Steps: {len(result.steps)}, Tool calls: {result.total_tool_calls}")

    await engine.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
