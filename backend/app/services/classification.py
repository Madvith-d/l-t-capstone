import re

from app.schemas.api import Intent

CALCULATION = re.compile(
    r"(?:\d|percent|percentage|calculate|what is).*(?:%|\+|\-|\*|/|of)", re.IGNORECASE
)


def classify_intent(question: str, has_plan: bool = False) -> Intent:
    value = question.strip().lower()
    if CALCULATION.search(value) and re.search(r"\d", value):
        return Intent.CALCULATION
    if any(
        term in value for term in ("study plan", "revision plan", "plan for", "schedule my study")
    ):
        return (
            Intent.STUDY_PLAN_MODIFICATION
            if has_plan
            and any(
                term in value for term in ("modify", "change", "move", "remove", "cannot", "can't")
            )
            else Intent.STUDY_PLAN
        )
    if has_plan and any(
        term in value for term in ("move ", "remove ", "cannot study", "only have")
    ):
        return Intent.STUDY_PLAN_MODIFICATION
    if any(
        term in value
        for term in ("find document", "search document", "which document", "show sources")
    ):
        return Intent.DOCUMENT_SEARCH
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
        )
    ):
        return Intent.ACADEMIC_QA
    if value in {"hi", "hello", "hey", "thanks", "thank you"}:
        return Intent.GENERAL_CONVERSATION
    return Intent.UNKNOWN
