"""Offline demo behavior evaluation; deliberately not an LLM accuracy benchmark."""

import json

from observatory.service import ABSTENTION, PortfolioAssistant, Settings

CASES = [
    ("Which projects are over budget?", {"PRJ-101", "PRJ-103"}),
    ("What are the risks for Cedar Claims?", {"PRJ-103"}),
    ("Summarize portfolio milestones", {"PRJ-101", "PRJ-102", "PRJ-103", "PRJ-104"}),
    ("Tell me about PRJ-999", set()),
    ("What is the weather?", set()),
]


def main():
    assistant = PortfolioAssistant(Settings())
    results = []
    for question, expected in CASES:
        answer = assistant.ask(question)
        actual = {p["id"] for p in answer["sources"]}
        passed = actual == expected and (bool(expected) or answer["answer"] == ABSTENTION)
        results.append({"question": question, "passed": passed, "sources": sorted(actual),
                        "elapsed_ms": answer["elapsed_ms"]})
    print(json.dumps({"mode": "offline-demo", "results": results,
                      "passed": sum(r["passed"] for r in results), "total": len(results)}, indent=2))
    assistant.close()
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
