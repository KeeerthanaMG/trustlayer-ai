"""Deterministic preflight for typed file actions on logical resources."""
import re
from dataclasses import dataclass
from pathlib import Path

from .policies import Decision, PolicyError, Rule, load_policies, match_policies


@dataclass(frozen=True)
class Evaluation:
    decision: Decision
    action: str
    resource: str
    risk: str
    consequence: str
    matched_policy_ids: tuple[str, ...]
    reason: str


_ACTIONS = {
    "file.read": ("low", "May disclose file contents to the caller."),
    "file.write": ("medium", "May create a file or overwrite existing contents."),
    "file.delete": ("high", "May remove the resource and its contents irreversibly."),
}
_RESOURCE_SEGMENT = re.compile(r"[a-zA-Z0-9_.-]+")


def classify_action(action: str) -> str | None:
    """Classify a supported typed action without interpreting shell text."""
    profile = _ACTIONS.get(action)
    return profile[0] if profile else None


def evaluate_consequences(action: str) -> str:
    profile = _ACTIONS.get(action)
    return profile[1] if profile else "The effect of this action is unknown."


def check_permissions(
    rules: tuple[Rule, ...], action: str, resource: str
) -> tuple[Decision, tuple[Rule, ...], str]:
    decision, matches = match_policies(rules, action, resource)
    if not matches:
        return decision, matches, "No policy grants permission for this action and resource."
    decisive_ids = ", ".join(rule.id for rule in matches if rule.decision == decision)
    return decision, matches, f"Policy rules requiring {decision.value}: {decisive_ids}."


def evaluate_action(policy_path: Path, action: str, resource: str) -> Evaluation:
    """Evaluate caller-supplied identifiers under an operator-selected policy."""
    risk = classify_action(action)
    consequence = evaluate_consequences(action)
    if risk is None:
        return Evaluation(Decision.BLOCK, action, resource, "unknown", consequence, (),
                          "Unsupported action type.")
    if any(
        not _RESOURCE_SEGMENT.fullmatch(segment) or segment.endswith(".")
        for segment in resource.split("/")
    ):
        return Evaluation(Decision.BLOCK, action, resource, risk, consequence, (),
                          "Expected a normalized logical resource identifier.")
    try:
        rules = load_policies(policy_path)
        for rule in rules:
            if rule.action != "*" and classify_action(rule.action) is None:
                raise PolicyError(f"Rule {rule.id} has an unsupported action type: {rule.action}")
        decision, matches, reason = check_permissions(rules, action, resource)
    except PolicyError as error:
        return Evaluation(Decision.BLOCK, action, resource, risk, consequence, (),
                          f"Policy error: {error}")
    return Evaluation(decision, action, resource, risk, consequence,
                      tuple(rule.id for rule in matches), reason)
