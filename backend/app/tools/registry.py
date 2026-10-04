"""LangChain tool registry for workflow-controlled external capabilities."""

from langchain_core.tools import StructuredTool

from app.tools.calculator import calculate


def get_calculator_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=calculate,
        name="calculator",
        description=(
            "Safely evaluate a mathematical expression, including questions such as "
            "'18% of 750'. This tool never executes arbitrary code."
        ),
    )


def get_tools() -> list[StructuredTool]:
    """Return tools available to the assistant; selection remains explicit in LangGraph."""
    return [get_calculator_tool()]
