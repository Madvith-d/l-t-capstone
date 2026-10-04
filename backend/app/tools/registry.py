"""LangChain tool registry for workflow-controlled external capabilities."""

from langchain_core.tools import StructuredTool

from app.tools.calculator import calculate
from app.tools.calendar import CalendarProvider


def get_calculator_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=calculate,
        name="calculator",
        description=(
            "Safely evaluate a mathematical expression, including questions such as "
            "'18% of 750'. This tool never executes arbitrary code."
        ),
    )


def get_calendar_tools(provider: CalendarProvider) -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            func=provider.create_event,
            name="calendar_create_event",
            description="Create a validated event in the user's mock calendar.",
        ),
        StructuredTool.from_function(
            func=provider.list_events,
            name="calendar_list_events",
            description="List events in the user's mock calendar.",
        ),
    ]


def get_tools(provider: CalendarProvider | None = None) -> list[StructuredTool]:
    """Return registered tools; selection remains explicit in LangGraph."""
    tools = [get_calculator_tool()]
    if provider is not None:
        tools.extend(get_calendar_tools(provider))
    return tools
