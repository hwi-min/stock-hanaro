#!/usr/bin/env python3
"""Validate the M0 data-source policy without third-party dependencies."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "data-sources.json"
ACTIONS = ("collect", "store", "display", "redistribute", "ai_input")
STATUSES = {"provisional", "restricted", "blocked", "approved"}


def validate_policy(policy: dict) -> list[str]:
    errors: list[str] = []
    if policy.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    try:
        date.fromisoformat(policy.get("reviewed_at", ""))
    except (TypeError, ValueError):
        errors.append("reviewed_at must be an ISO date")

    sources = policy.get("sources")
    if not isinstance(sources, list) or not sources:
        return errors + ["sources must be a non-empty list"]

    seen: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"{prefix}.id is required")
        elif source_id in seen:
            errors.append(f"{prefix}.id is duplicated: {source_id}")
        else:
            seen.add(source_id)

        status = source.get("status")
        if status not in STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(STATUSES)}")

        allowed = source.get("allowed")
        if not isinstance(allowed, dict) or set(allowed) != set(ACTIONS):
            errors.append(f"{prefix}.allowed must define exactly {ACTIONS}")
            continue
        if any(not isinstance(allowed[action], bool) for action in ACTIONS):
            errors.append(f"{prefix}.allowed values must be booleans")
        if status == "blocked" and any(allowed.values()):
            errors.append(f"{prefix} is blocked but allows an action")
        if allowed["redistribute"] and not allowed["display"]:
            errors.append(f"{prefix} cannot redistribute when display is false")
        if (allowed["store"] or allowed["display"] or allowed["ai_input"]) and not source.get("official_documents"):
            errors.append(f"{prefix} needs an official document for enabled use")
        if not isinstance(source.get("notes"), list) or not source["notes"]:
            errors.append(f"{prefix}.notes must be a non-empty list")

    return errors


def main() -> int:
    with POLICY_PATH.open(encoding="utf-8") as file:
        policy = json.load(file)
    errors = validate_policy(policy)
    if errors:
        print("Data-source policy validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(policy['sources'])} data sources ({policy['reviewed_at']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
