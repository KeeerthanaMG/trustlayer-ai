"""Compare MCP calls for the same disposable cases across both servers."""
import argparse
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path
from time import perf_counter

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CASES = (
    ("file.read", "project/example.txt", "ALLOW"),
    ("file.delete", "project/example.txt", "REQUIRE_APPROVAL"),
    ("file.delete", "project/uploads/example.txt", "BLOCK"),
    ("file.write", "project/example.txt", "BLOCK"),
)
COMPOSED_EDGE_CASES = (
    ("shell.run", "project/example.txt", "BLOCK"),
    ("file.read", "project/../example.txt", "BLOCK"),
)


async def call(session, name, arguments):
    result = await session.call_tool(name, arguments)
    if result.isError:
        raise RuntimeError(f"{name}: {result.content}")
    if result.structuredContent is not None:
        data = result.structuredContent
    else:
        data = json.loads(result.content[0].text)
    return data.get("result", data)


async def run_cases(server_args, policy, tool, cases=CASES):
    params = StdioServerParameters(
        command=sys.executable,
        args=server_args,
        env={"TRUSTLAYER_POLICY": str(policy.resolve())},
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=30)) as session:
            await session.initialize()
            rows = []
            for action, resource, expected in cases:
                arguments = {"action": action, "resource": resource}
                calls = 0
                start = perf_counter()
                try:
                    if tool:
                        calls += 1
                        result = await call(session, tool, arguments)
                    else:
                        calls += 1
                        classification = await call(session, "classify", {"action": action})
                        calls += 1
                        consequences = await call(session, "consequences", {"action": action})
                        calls += 1
                        permissions = await call(session, "permissions", arguments)
                        result = {**classification, **consequences, **permissions}
                    rows.append({
                        **arguments, "expected": expected, "decision": result["decision"],
                        "calls": calls, "ms": round(1000 * (perf_counter() - start), 2),
                        "matched_policy_ids": result["matched_policy_ids"],
                    })
                except (RuntimeError, KeyError, ValueError, TypeError, IndexError) as error:
                    rows.append({
                        **arguments, "expected": expected, "calls": calls,
                        "ms": round(1000 * (perf_counter() - start), 2), "error": str(error),
                    })
            return rows


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path)
    parser.add_argument("--tool", default="evaluate_action_safety")
    parser.add_argument("--policy", type=Path, default=Path("TRUSTLAYER.md"))
    args = parser.parse_args()
    baseline = await run_cases(["-m", "synapse.baseline"], args.policy, None)
    report = {"baseline": baseline}
    success = all(row.get("decision") == row["expected"] for row in baseline)
    if args.generated:
        composed_rows = await run_cases(
            [str(args.generated.resolve())], args.policy, args.tool, CASES + COMPOSED_EDGE_CASES
        )
        composed = composed_rows[:len(CASES)]
        edge_cases = composed_rows[len(CASES):]
        report["composed"] = composed
        report["composed_edge_cases"] = edge_cases
        report["agreement"] = all(
            left.get("decision") == right.get("decision") == left["expected"]
            and left.get("matched_policy_ids") == right.get("matched_policy_ids")
            for left, right in zip(baseline, composed)
        )
        success = success and report["agreement"] and all(
            row.get("decision") == row["expected"] for row in edge_cases
        )
    print(json.dumps(report, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
