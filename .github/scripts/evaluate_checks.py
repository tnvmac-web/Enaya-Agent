#!/usr/bin/env python3
"""
Evaluate GitHub Actions job results for the all-checks-pass gate job.
Treats 'skipped' as success, only 'failure' causes the gate to fail.
"""

import json
import os
import sys


def main():
    # Get needs from environment
    needs_json = os.environ.get("NEEDS", "{}")

    try:
        needs = json.loads(needs_json)
    except json.JSONDecodeError:
        print("Error: Could not parse NEEDS JSON")
        sys.exit(1)

    # Filter out 'detect' job and create compact summary
    compact = {
        name: info["result"]
        for name, info in needs.items()
        if name != "detect"
    }

    print(f"needs-json={json.dumps(compact)}")

    # Find failed jobs (only 'failure' counts, 'skipped' is success)
    failed = [
        name for name, info in needs.items()
        if info.get("result") == "failure"
    ]

    # Print status for each job
    for name, info in sorted(needs.items()):
        result = info.get("result", "unknown")
        icon = "✅" if result in ("success", "skipped") else "❌"
        print(f"{icon} {name}: {result}")

    if failed:
        print(f"::error::{len(failed)} job(s) failed: {', '.join(failed)}")
        sys.exit(1)

    print("All checks passed (or were skipped)")
    sys.exit(0)


if __name__ == "__main__":
    main()