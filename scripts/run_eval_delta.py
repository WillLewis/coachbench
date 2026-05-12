from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from _evaluation import write_json
except ModuleNotFoundError:
    from scripts._evaluation import write_json

try:
    import _path  # noqa: F401
except ModuleNotFoundError:
    from scripts import _path  # noqa: F401

from coachbench.contracts import ContractValidationError, validate_eval_delta_report, validate_eval_suite_report
from coachbench.eval_delta import build_delta_report


def _load_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ContractValidationError(f"could not load report {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractValidationError(f"report {path} must be object")
    return payload


def _exit_for_fail_on(report: dict[str, Any], mode: str) -> int:
    if mode == "never":
        return 0
    return 1 if report["regression"]["is_regression"] else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Diff two CoachBench eval suite reports.")
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--fail-on", choices=("never", "regression"), default="never")
    args = parser.parse_args()

    try:
        before = _load_report(args.before)
        after = _load_report(args.after)
        validate_eval_suite_report(before)
        validate_eval_suite_report(after)
        report = build_delta_report(before, after)
        validate_eval_delta_report(report)
    except ContractValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None

    write_json(args.out, report)
    lift = report["gate_transitions"]["lift_strength"]
    print(
        f"delta ok delta_hash={report['delta_hash'][:12]} "
        f"is_regression={report['regression']['is_regression']} "
        f"reasons={len(report['regression']['reasons'])} "
        f"lift_change={lift['before']}→{lift['after']}"
    )
    if args.fail_on == "regression" and report["regression"]["is_regression"]:
        for reason in report["regression"]["reasons"]:
            print(reason, file=sys.stderr)
    raise SystemExit(_exit_for_fail_on(report, args.fail_on))


if __name__ == "__main__":
    main()
