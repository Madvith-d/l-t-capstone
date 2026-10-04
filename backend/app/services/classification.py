import re

from app.schemas.api import Intent

ARITHMETIC_SYMBOLS = re.compile(r"(?:\d\s*[+*/%-]\s*\d|\d\s*-\s*\d)")
ARITHMETIC_WORDS = re.compile(
    r"\b(?:calculate|percent(?:age)?|times|multipl(?:y|ied)|divide|divided|add|plus|"
    r"subtract|minus|sum|product|quotient)\b",
    re.IGNORECASE,
)


def classify_intent(question: str, has_plan: bool = False) -> Intent:
    """Deterministic structured classifier with conservative academic fallback."""
    value = " ".join(question.strip().lower().split())
    if re.search(r"\d", value) and (
        ARITHMETIC_SYMBOLS.search(value)
        or ARITHMETIC_WORDS.search(value)
        or ("%" in value and len(re.findall(r"\d+(?:\.\d+)?", value)) >= 2)
    ):
        return Intent.CALCULATION
    if (
        any(term in value for term in ("calendar", "create an event", "add event"))
        or ("schedule " in value and ("tomorrow" in value or re.search(r"\bat\s+\d", value)))
    ):
        return Intent.CALENDAR_ACTION
    if any(
        term in value
        for term in ("find document", "search document", "which document", "show sources")
    ):
        return Intent.DOCUMENT_SEARCH
    if any(
        term in value
        for term in (
            "find ",
            "identify ",
            "compare ",
            " and then ",
            "list their",
        )
    ) and any(term in value for term in ("course", "subject", "semester", "rule", "document")):
        return Intent.MULTI_STEP
    modification_terms = (
        "modify",
        "change",
        "move",
        "remove",
        "cannot study",
        "can't study",
        "only have",
        "reschedule",
    )
    if has_plan and any(term in value for term in modification_terms):
        return Intent.STUDY_PLAN_MODIFICATION
    if any(
        term in value for term in ("study plan", "revision plan", "plan for", "schedule my study")
    ):
        if any(term in value for term in modification_terms):
            return Intent.STUDY_PLAN_MODIFICATION
        return Intent.STUDY_PLAN
    if any(
        term in value
        for term in (
            "attendance",
            "semester",
            "syllabus",
            "exam",
            "assessment",
            "college",
            "course",
            "subject",
            "regulation",
            "rule",
            "policy",
            "practical",
            "credit",
            "project requirement",
        )
    ):
        return Intent.ACADEMIC_QA
    if value in {"hi", "hello", "hey", "thanks", "thank you", "help"}:
        return Intent.GENERAL_CONVERSATION
    return Intent.UNKNOWN
