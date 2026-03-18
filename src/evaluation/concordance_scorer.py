"""Partial-credit scorer for NCCN guideline concordance verdicts."""


def score_concordance(question: str, predicted: str, ground_truth: str) -> float:
    def norm(s: str) -> str:
        return s.strip().upper().replace("NON-CONCORDANT", "NON_CONCORDANT")
    p, g = norm(predicted), norm(ground_truth)
    if p == g:
        return 1.0
    if "EXCLUDED" in (p, g):
        return 0.5
    return 0.0
