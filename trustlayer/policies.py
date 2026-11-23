"""Parse and match operator-selected Markdown policies."""
import json
import re
from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatchcase
from pathlib import Path

POLICY_BLOCK = re.compile(r"^```trustlayer[ \t]*\n(.*?)^\`\`\`[ \t]*$", re.MULTILINE | re.DOTALL)


class PolicyError(ValueError):
    """A policy could not be loaded or validated."""


class Decision(str, Enum):
    BLOCK = "BLOCK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    ALLOW = "ALLOW"


@dataclass(frozen=True)
class Rule:
    id: str
    action: str
    resource: str
    decision: Decision


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_policies(path: Path) -> tuple[Rule, ...]:
    """Load the single versioned policy block from a trusted Markdown file."""
    try:
        markdown = path.read_text(encoding="utf-8-sig")
        blocks = POLICY_BLOCK.findall(markdown)
        if len(blocks) != 1:
            raise PolicyError("Expected exactly one fenced trustlayer policy block")
        data = json.loads(blocks[0], object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PolicyError(f"Could not read policy {path}: {error}") from error

    if (
        not isinstance(data, dict)
        or data.keys() != {"version", "rules"}
        or type(data["version"]) is not int
        or data["version"] != 1
        or not isinstance(data["rules"], list)
    ):
        raise PolicyError("Expected version 1 and a rules array")

    rules = []
    ids = set()
    for index, item in enumerate(data["rules"], start=1):
        if (
            not isinstance(item, dict)
            or item.keys() != {"id", "action", "resource", "decision"}
            or any(not isinstance(value, str) or not value.strip() for value in item.values())
        ):
            raise PolicyError(f"Rule {index} must contain id, action, resource, and decision strings")
        if item["id"] in ids:
            raise PolicyError(f"Duplicate rule id: {item['id']}")
        if not re.fullmatch(r"\*|[a-z][a-z0-9_.-]*", item["action"]):
            raise PolicyError(f"Rule {index} has an invalid action")
        if any(character in item["resource"] for character in "?[]"):
            raise PolicyError(f"Rule {index} resource patterns support only the * wildcard")
        try:
            decision = Decision(item["decision"])
        except ValueError as error:
            raise PolicyError(f"Rule {index} has an unsupported decision") from error
        ids.add(item["id"])
        rules.append(Rule(item["id"], item["action"], item["resource"], decision))
    return tuple(rules)


def match_policies(rules: tuple[Rule, ...], action: str, resource: str) -> tuple[Decision, tuple[Rule, ...]]:
    """Match one normalized action and resource, with deny-by-default precedence."""
    if not re.fullmatch(r"[a-z][a-z0-9_.-]*", action) or not resource.strip():
        raise PolicyError("Expected a normalized action and a nonempty resource")
    matches = tuple(
        rule for rule in rules
        if rule.action in (action, "*") and fnmatchcase(resource, rule.resource)
    )
    for decision in Decision:
        if any(rule.decision == decision for rule in matches):
            return decision, matches
    return Decision.BLOCK, matches
