import json
import os
import re
from pathlib import Path

from app.db.session import SessionLocal
from app.services.llm import get_llm_service
from app.services.prompts import UNKNOWN_RESPONSE
from app.services.rag import RAGService
from app.services.retrieval import Retriever


def evaluation_dir() -> Path:
    candidates = [
        Path(os.environ["EVALUATION_DIR"]) if os.getenv("EVALUATION_DIR") else None,
        Path(__file__).resolve().parents[2] / "evaluation",
        Path("/app/evaluation"),
        Path.cwd() / "evaluation",
        Path.cwd().parent / "evaluation",
    ]
    for candidate in candidates:
        if candidate and (candidate / "dataset.json").exists():
            return candidate
    raise FileNotFoundError("evaluation/dataset.json was not found; mount it at /app/evaluation")


def relevance(question: str, answer: str) -> float:
    stop = {"what", "when", "which", "that", "this", "with", "from", "have", "does"}
    q_terms = {word for word in re.findall(r"[a-z]+", question.lower()) if word not in stop}
    a_terms = set(re.findall(r"[a-z]+", answer.lower()))
    return round(len(q_terms & a_terms) / max(1, len(q_terms)), 3)


def run() -> None:
    directory = evaluation_dir()
    dataset = json.loads((directory / "dataset.json").read_text(encoding="utf-8"))
    llm = get_llm_service()
    results = []
    with SessionLocal() as db:
        rag = RAGService(Retriever(db), llm)
        for item in dataset:
            rag_answer, sources, confidence = rag.answer(item["question"], item.get("history"))
            baseline = llm.baseline(item["question"])
            expected = item.get("expected_contains")
            correctness = (
                expected.lower() in rag_answer.lower()
                if expected
                else rag_answer == UNKNOWN_RESPONSE if item["category"] == "unknown" else None
            )
            results.append(
                {
                    **item,
                    "baseline_answer": baseline,
                    "rag_answer": rag_answer,
                    "sources": [source.model_dump() for source in sources],
                    "confidence": confidence,
                    "correctness": correctness,
                    "grounding": bool(sources) and bool(re.search(r"\[\d+\]", rag_answer)),
                    "relevance": relevance(item["question"], rag_answer),
                    "follow_up_handling": (
                        bool(sources) and rag_answer != UNKNOWN_RESPONSE
                        if item["category"] == "follow_up"
                        else None
                    ),
                    "unsupported_answer": not sources and rag_answer != UNKNOWN_RESPONSE,
                }
            )
    output = directory / "results.json"
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    measured = [row for row in results if row["correctness"] is not None]
    summary = {
        "questions": len(results),
        "measured_correctness": (
            sum(bool(row["correctness"]) for row in measured) / len(measured) if measured else None
        ),
        "grounding_rate": sum(row["grounding"] for row in results) / len(results),
        "unsupported_answer_rate": sum(row["unsupported_answer"] for row in results) / len(results),
        "mean_relevance": sum(row["relevance"] for row in results) / len(results),
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {len(results)} paired results to {output}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run()
