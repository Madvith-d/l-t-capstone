from datetime import UTC, datetime

import pytest

from app.schemas.api import Intent
from app.services.classification import classify_intent
from app.tools.calculator import CalculatorError, calculate
from app.tools.calendar import MockCalendarProvider


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("What is the attendance rule?", Intent.ACADEMIC_QA),
        ("Create a study plan.", Intent.STUDY_PLAN),
        ("What is 20% of 500?", Intent.CALCULATION),
        ("Hello", Intent.GENERAL_CONVERSATION),
        ("Find document about examinations", Intent.DOCUMENT_SEARCH),
    ],
)
def test_intents(question, intent):
    assert classify_intent(question) == intent


def test_calculator_percentage():
    assert calculate("What is 18% of 750?") == 135


def test_mock_calendar_uses_replaceable_provider_contract():
    calendar = MockCalendarProvider()
    event = calendar.create_event("DBMS revision", datetime(2026, 11, 1, 19, tzinfo=UTC), 60)
    assert event in calendar.list_events()


def test_calculator_rejects_code():
    with pytest.raises(CalculatorError):
        calculate("__import__('os').system('id')")
