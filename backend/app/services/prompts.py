"""Reusable LangChain prompt templates used by generation and planning features."""

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

ACADEMIC_QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a college academic assistant. Use only the supplied document context "
                "for college-specific facts. Cite supporting passages with their source markers, "
                "such as [1]. If the context is insufficient, reply exactly: {unknown_response}"
            ),
        ),
        (
            "human",
            "Document context:\n{context}\n\nStudent question: {question}",
        ),
    ]
)

SUMMARIZATION_PROMPT = PromptTemplate.from_template(
    "Summarize the following approved academic material without adding facts. Preserve "
    "deadlines, requirements, exceptions, and source markers.\n\n{context}"
)

STUDY_PLANNING_PROMPT = PromptTemplate.from_template(
    "Create a study-plan proposal for these subjects: {subjects}. The student has "
    "{available_hours} hours per day until {exam_date}. Respect these constraints: "
    "{constraints}. Return a concise proposal; dates and workload must still be validated "
    "by the deterministic planner."
)

UNKNOWN_RESPONSE = "I couldn't find information about this in the available college documents."


def render_academic_prompt(question: str, context: str) -> str:
    """Render a provider-neutral prompt while keeping the template reusable and testable."""
    messages = ACADEMIC_QA_PROMPT.format_messages(
        question=question,
        context=context,
        unknown_response=UNKNOWN_RESPONSE,
    )
    return "\n\n".join(str(message.content) for message in messages)
