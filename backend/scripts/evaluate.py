import json
from pathlib import Path

from app.db.session import SessionLocal
from app.services.llm import get_llm_service
from app.services.rag import RAGService
from app.services.retrieval import Retriever


def run() -> None:
    dataset = json.loads(Path("../evaluation/dataset.json").read_text())
    llm = get_llm_service()
    results = []
    with SessionLocal() as db:
        rag = RAGService(Retriever(db), llm)
        for item in dataset:
            rag_answer, sources, confidence = rag.answer(item["question"], item.get("history"))
            baseline = llm.baseline(item["question"])
            results.append(
                {
                    **item,
                    "baseline_answer": baseline,
                    "rag_answer": rag_answer,
                    "sources": [s.model_dump() for s in sources],
                    "confidence": confidence,
                    "evaluation_notes": {
                        "correctness": None,
                        "grounding": bool(sources),
                        "relevance": None,
                        "follow_up_handled": None,
                    },
                }
            )
    output = Path("../evaluation/results.json")
    output.write_text(json.dumps(results, indent=2))
    print(f"Wrote {len(results)} paired results to {output}")


if __name__ == "__main__":
    run()
