"""Agent API — run the agent loop directly with full step details."""
from fastapi import APIRouter
from app.core.engine import engine
from app.schemas.tool import AgentRequest, AgentResponse, AgentStepInfo

router = APIRouter(tags=["agent"])


@router.post("/agent/run", response_model=AgentResponse)
async def run_agent(req: AgentRequest):
    """Run the agent with full control and step-by-step results."""
    result = await engine.run_agent(
        message=req.message,
        system_prompt=req.system_prompt,
        conversation=req.conversation,
        session_id=req.session_id,
        max_iterations=req.max_iterations,
    )

    steps = []
    for s in result.steps:
        steps.append(AgentStepInfo(
            step_number=s.step_number,
            reasoning=s.reasoning,
            tool_calls=[
                {"tool": tc.tool_name, "args": tc.arguments,
                 "result": tc.result[:500], "duration_ms": tc.duration_ms}
                for tc in s.tool_calls
            ],
            response=s.response,
        ))

    return AgentResponse(
        response=result.response,
        steps=steps,
        total_tool_calls=result.total_tool_calls,
        total_duration_ms=result.total_duration_ms,
    )
