"""
MCP Tools Example — connect external MCP servers and let the agent use them.

Create an omnibot.json in the project root:
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    }
  }
}

Then run:
    python examples/mcp_tools.py
"""
import asyncio
from app.core.engine import AgentEngine


async def main():
    engine = AgentEngine()
    await engine.initialize("omnibot.json")

    # The agent will automatically discover and use MCP tools
    print(f"Available tools: {engine.registry.tool_names}")

    # Ask something that requires tools
    result = await engine.run_agent(
        "List the files in the ./data directory"
    )
    print(f"\nResponse: {result.response}")

    # Show what happened under the hood
    for step in result.steps:
        print(f"\n--- Step {step.step_number} ---")
        if step.reasoning:
            print(f"Reasoning: {step.reasoning[:200]}")
        for tc in step.tool_calls:
            print(f"Tool: {tc.tool_name}({tc.arguments}) \u2192 {tc.result[:100]}...")
        if step.response:
            print(f"Final: {step.response[:200]}")

    await engine.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
