"""Deterministic demo content. Nothing in this module represents real college policy."""

import re
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_user
from app.models import Conversation, Message, MessageRole, StudyPlan
from app.schemas.api import PlanCreate, SubjectInput
from app.services.prompts import UNKNOWN_RESPONSE

DEMO_NOTICE = "Presentation dataset active."
DEMO_SOURCES = {
    "regulations": {
        "document_id": "demo-academic-regulations",
        "title": "Sample Academic Regulations",
        "page": 1,
        "section": "Attendance and examinations",
        "category": "regulations",
        "department": "All departments",
        "academic_year": "2026–27",
        "source": "Sample Academic Regulations.txt",
        "score": 1.0,
    },
    "syllabus": {
        "document_id": "demo-semester-four-syllabus",
        "title": "Sample Semester Four Syllabus",
        "page": 1,
        "section": "Semester 4 curriculum",
        "category": "syllabus",
        "department": "Computer Science",
        "academic_year": "2026–27",
        "source": "Sample Semester Four Syllabus.txt",
        "score": 1.0,
    },
}

DEMO_QUESTIONS = [
    "What is the attendance requirement?",
    "What happens if I do not meet the attendance requirement?",
    "What are the examination guidelines?",
    "How is internal assessment calculated?",
    "What subjects are present in semester 4?",
    "Which courses have practical examinations?",
    "What are the project requirements and deadlines?",
    "Find the semester 4 subjects and identify the practical courses.",
    "What will the cafeteria serve next Tuesday?",
]


def demo_plan_request(today: date | None = None) -> PlanCreate:
    start = today or date.today()
    return PlanCreate(
        title="Examination preparation plan",
        subjects=[
            SubjectInput(
                name="DBMS",
                topics=["SQL", "Normalization", "Transactions"],
                difficulty=4,
            ),
            SubjectInput(
                name="Operating Systems",
                topics=["Scheduling", "Memory management"],
                difficulty=3,
            ),
        ],
        start_date=start,
        exam_date=start + timedelta(days=14),
        available_hours_per_day=3,
        preferred_times=["evening"],
    )


def demo_plan_requests(today: date | None = None) -> list[PlanCreate]:
    start = today or date.today()
    return [
        demo_plan_request(start),
        PlanCreate(
            title="Semester revision plan",
            subjects=[
                SubjectInput(
                    name="Computer Networks",
                    topics=["Routing", "Transport layer", "Network security"],
                    difficulty=4,
                ),
                SubjectInput(
                    name="Algorithms",
                    topics=["Dynamic programming", "Graphs"],
                    difficulty=5,
                ),
            ],
            start_date=start,
            exam_date=start + timedelta(days=21),
            available_hours_per_day=2.5,
            preferred_times=["morning"],
        ),
    ]


def ensure_demo_plans(db: Session, user_id: str) -> list[StudyPlan]:
    from app.services.plans import create_plan

    ensure_user(db, user_id)
    expected = demo_plan_requests()
    existing = list(
        db.scalars(
            select(StudyPlan).where(
                StudyPlan.user_id == user_id,
                StudyPlan.title.in_([request.title for request in expected]),
            )
        ).all()
    )
    existing_titles = {plan.title for plan in existing}
    for request in expected:
        if request.title not in existing_titles:
            existing.append(create_plan(db, user_id, request))
    db.flush()
    return existing


def ensure_demo_conversations(db: Session, user_id: str) -> list[Conversation]:
    ensure_user(db, user_id)
    examples = [
        (
            "Attendance and eligibility",
            [
                ("user", "What is the attendance requirement?", []),
                (
                    "assistant",
                    "Students must maintain at least 85 percent attendance in each course to be eligible for the end-semester examination. [1]",
                    [DEMO_SOURCES["regulations"]],
                ),
                ("user", "What happens if I do not meet it?", []),
                (
                    "assistant",
                    "A student below 85 percent attendance must meet the academic adviser and may be declared ineligible for the examination unless an approved exception applies. [1]",
                    [DEMO_SOURCES["regulations"]],
                ),
                ("user", "Does the document describe the exception process?", []),
                (
                    "assistant",
                    "I couldn't find information about the exception process in the available college documents.",
                    [],
                ),
            ],
        ),
        (
            "Semester 4 practical courses",
            [
                ("user", "What subjects are present in semester 4?", []),
                (
                    "assistant",
                    "Semester 4 contains DBMS, Operating Systems, Computer Networks, and Design and Analysis of Algorithms. [1]",
                    [DEMO_SOURCES["syllabus"]],
                ),
                ("user", "Which of those subjects have practicals?", []),
                (
                    "assistant",
                    "DBMS, Operating Systems, and Computer Networks include laboratory practicals. [1]",
                    [DEMO_SOURCES["syllabus"]],
                ),
                ("user", "Does Design and Analysis of Algorithms have one?", []),
                (
                    "assistant",
                    "Design and Analysis of Algorithms has no separate practical examination. [1]",
                    [DEMO_SOURCES["syllabus"]],
                ),
            ],
        ),
        (
            "Study plan adjustment",
            [
                ("user", "Create a 14-day study plan for DBMS and Operating Systems.", []),
                (
                    "assistant",
                    "I created a validated plan covering SQL, normalization, transactions, scheduling, and memory management within a three-hour daily limit.",
                    [],
                ),
                ("user", "I cannot study on Saturday.", []),
                (
                    "assistant",
                    "Saturday sessions were redistributed before the examination date. Unaffected sessions kept their IDs and progress status.",
                    [],
                ),
                ("user", "I only have one hour tomorrow.", []),
                (
                    "assistant",
                    "Tomorrow's workload was limited to one hour and the remaining work was moved to available days before the examination.",
                    [],
                ),
            ],
        ),
    ]
    conversations: list[Conversation] = []
    for index, (title, messages) in enumerate(examples, 1):
        marker = f"demo:seed:v3:{index}"
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.summary == marker,
            )
        )
        if conversation is None:
            conversation = Conversation(user_id=user_id, title=title, summary=marker)
            db.add(conversation)
            db.flush()
            db.add_all(
                [
                    Message(
                        conversation_id=conversation.id,
                        role=MessageRole(role),
                        content=content,
                        sources=sources,
                    )
                    for role, content, sources in messages
                ]
            )
        conversations.append(conversation)
    db.flush()
    return conversations


def _answer(text: str, source: str) -> tuple[str, list[dict], float]:
    return f"{text[0].upper()}{text[1:]} [1]", [DEMO_SOURCES[source]], 1.0


def demo_answer(question: str, history: list[dict] | None = None) -> tuple[str, list[dict], float]:
    value = " ".join(question.lower().split())
    if re.search(r"cafeteria|graduation gown|student election|late registration|credit requirements", value):
        return UNKNOWN_RESPONSE, [], 0.0
    if "attendance" in value:
        if re.search(r"below|do not meet|don't meet|happens|ineligible", value):
            return _answer(
                "a student below 85 percent attendance must meet the academic adviser and may be declared ineligible for the examination unless an approved exception applies.",
                "regulations",
            )
        return _answer(
            "students must maintain at least 85 percent attendance in each course to be eligible for the end-semester examination.",
            "regulations",
        )
    if re.search(r"what happens if .*\b(it|that)\b", value):
        recent = " ".join(
            str(message.get("content", "")).lower() for message in (history or [])[-4:]
        )
        if "attendance" in recent:
            return _answer(
                "a student below 85 percent attendance must meet the academic adviser and may be declared ineligible for the examination unless an approved exception applies.",
                "regulations",
            )
    if "internal assessment" in value:
        return _answer(
            "internal assessment consists of two tests worth 20 marks each and one assignment worth 10 marks.",
            "regulations",
        )
    if "examination guideline" in value or "exam guideline" in value:
        return _answer(
            "students must bring their identity card, arrive thirty minutes early, and keep prohibited electronic devices outside the examination room.",
            "regulations",
        )
    if "semester 4" in value or "semester four" in value:
        subjects = "DBMS, Operating Systems, Computer Networks, and Design and Analysis of Algorithms"
        if "practical" in value or "identify" in value:
            return _answer(
                f"semester 4 contains {subjects}. DBMS, Operating Systems, and Computer Networks include laboratory practicals; Design and Analysis of Algorithms has no separate practical examination.",
                "syllabus",
            )
        return _answer(f"semester 4 contains {subjects}.", "syllabus")
    if "practical" in value:
        return _answer(
            "DBMS, Operating Systems, and Computer Networks include laboratory practicals. Design and Analysis of Algorithms has no separate practical examination.",
            "syllabus",
        )
    if "project" in value and any(term in value for term in ("requirement", "deadline", "due")):
        return _answer(
            "the sample mini-project requires a proposal, implementation, and presentation. The sample proposal deadline is March 10 and the final presentation deadline is April 25.",
            "syllabus",
        )
    return UNKNOWN_RESPONSE, [], 0.0


def demo_documents() -> list[dict]:
    created = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        {
            "id": source["document_id"],
            "title": source["title"],
            "category": source["category"],
            "department": source["department"],
            "academic_year": source["academic_year"],
            "source": source["source"],
            "status": "ready",
            "created_at": created,
        }
        for source in DEMO_SOURCES.values()
    ]
