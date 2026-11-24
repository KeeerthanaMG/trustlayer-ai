"""Approval-gated deletion of named disposable fixtures."""
import argparse
import json
import stat
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from .engine import Evaluation, evaluate_action
from .policies import Decision

FIXTURES = {"project/example.txt", "project/uploads/example.txt"}


def request_approval(evaluation: Evaluation, target: Path, timeout: float = 30) -> bool:
    review = {**asdict(evaluation), "target": str(target)}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "trustlayer.approval_dialog"],
            input=json.dumps(review), capture_output=True, text=True, timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "approved"


def fixture_state(root: Path, resource: str):
    target = root / resource
    relative = Path(resource)
    paths = (root / parent for parent in reversed(relative.parents))
    for path in (*paths, target):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Fixture paths cannot contain links or reparse points.")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("The target must be a regular disposable file without other links.")
    return target, (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def delete_fixture(policy: Path, root: Path, resource: str, approve=request_approval) -> dict:
    """Evaluate and execute one fixed demo action in an operator-controlled directory."""
    if resource not in FIXTURES:
        return {"executed": False, "decision": "BLOCK", "reason": "Unknown disposable fixture."}
    evaluation = evaluate_action(policy, "file.delete", resource)
    result = {**asdict(evaluation), "executed": False}
    if evaluation.decision == Decision.BLOCK:
        return result

    try:
        root = root.absolute()
        target, state = fixture_state(root, resource)
        if evaluation.decision == Decision.REQUIRE_APPROVAL and not approve(evaluation, target):
            return {**result, "reason": "Approval declined, unavailable, or expired."}
        if (
            fixture_state(root, resource) != (target, state)
            or evaluate_action(policy, "file.delete", resource) != evaluation
        ):
            return {**result, "reason": "The target or applicable policy changed. Evaluate again."}
        target.unlink()
    except (OSError, ValueError) as error:
        return {**result, "reason": f"Fixture action stopped: {error}"}
    return {**result, "executed": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("resource")
    args = parser.parse_args()
    result = delete_fixture(args.policy, args.fixture_root, args.resource)
    print(json.dumps(result, indent=2))
    return 0 if result["executed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
