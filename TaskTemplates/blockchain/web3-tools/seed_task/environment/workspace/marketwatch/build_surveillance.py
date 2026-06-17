from __future__ import annotations

import sys


def main() -> int:
    raise NotImplementedError(
        "Implement the market surveillance delivery in this workspace project. "
        "The final script must read the task manifest, query the local service, "
        "and write the required outputs under /app/output/surveillance."
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NotImplementedError as exc:
        print(str(exc), file=sys.stderr)
        raise

