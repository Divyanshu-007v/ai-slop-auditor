"""
Evaluation Runner — runs the full pipeline on test claims and reports accuracy.

Usage:
    python evaluation/eval_runner.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator_agent import OrchestratorAgent
from models import VerdictLabel


def load_test_claims() -> list[dict]:
    """Load test claims from test_claims.json."""
    path = Path(__file__).parent / "test_claims.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_claims"]


def run_evaluation():
    """Run full pipeline on test claims and compare with expected results."""
    print("=" * 60)
    print("AI-Slop Auditor — Evaluation Runner")
    print("=" * 60)

    test_claims = load_test_claims()
    orchestrator = OrchestratorAgent()

    correct = 0
    total = 0
    results = []

    for tc in test_claims:
        claim_text = tc["claim_text"]
        expected_verdict = tc["expected_verdict"]
        expected_min = tc["expected_min_score"]
        expected_max = tc["expected_max_score"]

        # Skip opinion test cases
        if expected_verdict == "skip":
            print(f"\n⏭ SKIP (opinion): {claim_text}")
            continue

        total += 1
        print(f"\n--- Claim {total}: {claim_text} ---")

        # Run the pipeline on just this claim
        report = orchestrator.run_audit(claim_text)

        if report.verdicts:
            verdict = report.verdicts[0]
            predicted = verdict.verdict.value
            score = verdict.trust_score

            # Check if score is in expected range
            score_ok = expected_min <= score <= expected_max

            # Check verdict (loose matching)
            verdict_ok = _verdict_matches(predicted, expected_verdict)

            is_correct = score_ok or verdict_ok
            if is_correct:
                correct += 1

            status = "✅" if is_correct else "❌"
            results.append({
                "claim": claim_text,
                "expected": expected_verdict,
                "predicted": predicted,
                "score": score,
                "expected_range": f"{expected_min}-{expected_max}",
                "score_ok": score_ok,
                "verdict_ok": verdict_ok,
                "correct": is_correct,
            })

            print(f"  Expected: {expected_verdict} (score {expected_min}-{expected_max})")
            print(f"  Got:      {predicted} (score {score})")
            print(f"  {status}")
        else:
            print(f"  ❌ No verdict produced")
            results.append({
                "claim": claim_text,
                "expected": expected_verdict,
                "predicted": "NO VERDICT",
                "score": 0,
                "correct": False,
            })

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {correct}/{total} correct ({correct/total*100:.1f}% accuracy)")
    print("=" * 60)

    for r in results:
        status = "✅" if r["correct"] else "❌"
        print(f"  {status} {r['claim'][:50]:50s} | Expected: {r['expected']:25s} | Got: {r['predicted']:25s} | Score: {r.get('score', 'N/A')}")

    return results


def _verdict_matches(predicted: str, expected: str) -> bool:
    """Loose verdict matching (handles different label formats)."""
    p = predicted.lower().strip()
    e = expected.lower().strip()

    # Direct match
    if p == e:
        return True

    # Map variations
    mapping = {
        "supported": ["supported", "mostly supported"],
        "mostly supported": ["mostly supported", "supported"],
        "unsupported": ["unsupported", "contradicted", "needs human review"],
        "contradicted": ["contradicted", "unsupported"],
        "insufficient evidence": ["insufficient evidence", "needs human review"],
        "needs human review": ["needs human review", "insufficient evidence", "unsupported"],
    }

    return p in mapping.get(e, [])


if __name__ == "__main__":
    run_evaluation()
