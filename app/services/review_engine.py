"""Coordinates language analyzers, evidence, scoring and quality metrics."""
from app.services.analyzer_registry import analyze
from app.services.ai_provider import ACTIONS  # noqa: F401 - exported for API discovery
from app.services.evidence_engine import build_evidence
from app.services.fix_engine import validate_fix
from app.services.uncertainty_engine import calculate_uncertainty
from app.utils.confidence_calculator import calculate_confidence, classify_confidence, confidence_factors

SEVERITY_RANK = {"Critical": 5, "High": 4, "Medium": 3, "Low": 2, "Informational": 1}
SEVERITY_PENALTY = {"Critical": 20, "High": 10, "Medium": 5, "Low": 2, "Informational": 0}
MODE_CATEGORIES = {
    "bugs": {"Bug", "Syntax"},
    "security": {"Security"},
    "performance": {"Performance"},
    "quality": {"Quality"},
}


class ReviewResult(list):
    """A findings list that also carries project-level analysis metadata."""

    def __init__(self, items, metrics, quality_score, risk_level):
        super().__init__(items)
        self.metrics = metrics
        self.quality_score = quality_score
        self.risk_level = risk_level


def _quality_score(findings, metrics):
    penalty = sum(SEVERITY_PENALTY.get(item["severity"], 0) * (.5 + item["confidence"] * .5) for item in findings)
    penalty += max(0, metrics.get("max_complexity", 0) - 8) * 1.5
    penalty += max(0, metrics.get("max_nesting", 0) - 4) * 2
    return round(max(0.0, min(100.0, 100 - penalty)), 1)


def _risk_level(findings):
    high_confirmed = [f for f in findings if f["severity"] in {"High", "Critical"} and f["confidence"] >= .7]
    if any(f["severity"] == "Critical" and f["confidence"] >= .7 for f in findings):
        return "Critical"
    if len(high_confirmed) >= 2:
        return "High"
    if high_confirmed or sum(1 for f in findings if f["severity"] == "Medium") >= 3:
        return "Medium"
    return "Low"


def review_code(code, language="python", mode="comprehensive", sensitivity="balanced", file_name="submitted_code.py"):
    raw, metrics, full_analysis = analyze(code, language)
    if mode in MODE_CATEGORIES:
        raw = [item for item in raw if item.get("category") in MODE_CATEGORIES[mode]]

    results = []
    seen = set()
    for item in raw:
        identifier = item.get("rule_id") or item.get("title", "")
        key = (identifier, item.get("line", 1), item.get("column", 1), file_name)
        if key in seen:
            continue
        seen.add(key)
        factors = {name: item.get(name) for name in ("reliability", "strength", "certainty", "context", "independent")}
        confidence = calculate_confidence(factors, item.get("verified", False))
        if sensitivity == "conservative" and confidence < .68:
            continue
        uncertainty = calculate_uncertainty(
            confidence,
            context_missing=item.get("context", 0) < .7,
            context_dependent=item.get("context_dependent", False),
            context_completeness=item.get("context"),
            detection_certainty=item.get("certainty"),
        )
        explanation = confidence_factors(factors, item.get("verified", False))
        fix = validate_fix(item.get("suggested_fix", ""), language)
        rationale_parts = []
        for row in explanation["rows"]:
            value_text = f"{row['value']:.0%}" if row["available"] else "unavailable"
            rationale_parts.append(f"{row['label']}: {value_text}")
        rationale = (
            "Evidence-weighted estimate (" + ", ".join(rationale_parts) + "). "
            + ("A deterministic floor of 82% applies to verified syntactic observations. " if item.get("verified") else "")
            + "These are heuristic estimates, not empirically calibrated probabilities."
        )
        item.update(
            confidence=confidence,
            uncertainty=uncertainty,
            confidence_level=classify_confidence(confidence),
            rule_id=identifier,
            file_name=file_name,
            explanation=item.get("explanation") or item.get("description", ""),
            score_factors=explanation,
            rationale=rationale,
            fix_code=item.get("suggested_fix", ""),
            fix_valid=fix["syntax_valid"],
            evidence=[build_evidence(item["source"], item.get("evidence_description", item.get("description", "")), item["strength"], item["verified"])],
            snippet=item.get("snippet", ""),
            limited_analysis=not full_analysis,
        )
        if item["severity"] in {"High", "Critical"} and confidence < .5:
            item["warning"] = "Potentially serious issue, but supporting evidence is weak. Manual verification is strongly recommended."
        results.append(item)

    results.sort(key=lambda f: (SEVERITY_RANK.get(f["severity"], 0), f["confidence"], f.get("strength", 0)), reverse=True)
    metrics = dict(metrics)
    metrics["full_analysis"] = full_analysis
    return ReviewResult(results, metrics, _quality_score(results, metrics), _risk_level(results))
