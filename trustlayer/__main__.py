"""Run standalone TrustLayer policy evaluation."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .engine import evaluate_action
from .policies import Decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True, help="Operator-selected Markdown policy")
    parser.add_argument("action", help="Typed action, such as file.read")
    parser.add_argument("resource", help="Logical resource, such as project/example.txt")
    args = parser.parse_args()
    result = evaluate_action(args.policy, args.action, args.resource)
    print(json.dumps(asdict(result), indent=2))
    return {Decision.ALLOW: 0, Decision.REQUIRE_APPROVAL: 3, Decision.BLOCK: 4}[result.decision]


if __name__ == "__main__":
    raise SystemExit(main())
