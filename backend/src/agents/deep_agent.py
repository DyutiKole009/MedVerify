"""LangGraph Deep Agent with Bedrock tool-calling and bounded execution."""
from typing import Any, Annotated, TypedDict

from src.config import settings
from src.tools.deep_tools import DEEP_TOOLS


class DeepAgentState(TypedDict):
    """Messages exchanged by the Deep Agent graph."""
    messages: Annotated[list[Any], "conversation messages"]


def create_deep_agent(**kwargs: Any) -> Any:
    """Create a bounded LangGraph agent using a Bedrock Converse model."""
    try:
        from langchain_aws import ChatBedrockConverse
        from langgraph.graph import END, START, StateGraph
        from langgraph.prebuilt import ToolNode, tools_condition
    except ImportError as error:
        raise RuntimeError("Install langgraph and langchain-aws to create the Deep Agent") from error

    max_tool_calls = int(kwargs.pop("max_tool_calls", 8))
    tools = DEEP_TOOLS
    model = kwargs.pop("model", settings.BEDROCK_DEEP_AGENT_MODEL_ID)
    llm = ChatBedrockConverse(
        model=model,
        region_name=settings.AWS_REGION,
        temperature=0,
        max_tokens=kwargs.pop("max_tokens", 2048),
        **kwargs,
    ).bind_tools(tools)

    def reason(state: DeepAgentState) -> dict[str, list[Any]]:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)
    graph = StateGraph(DeepAgentState)
    graph.add_node("reason", reason)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "reason")
    graph.add_conditional_edges("reason", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "reason")

    compiled = graph.compile()

    def invoke(messages: list[Any]) -> dict[str, Any]:
        return compiled.invoke(
            {"messages": messages},
            config={"recursion_limit": max_tool_calls * 2 + 1},
        )

    return invoke