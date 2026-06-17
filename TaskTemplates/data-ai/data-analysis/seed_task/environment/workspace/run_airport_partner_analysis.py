#!/usr/bin/env python3

import argparse
from pathlib import Path


def main() -> None:
    # Build the analysis pipeline so the shared entrypoint can:
    # 1. Read /root/data/planning/analysis_contract.json and apply all contract-driven rules.
    # 2. Harmonize dispatch_batch_a..d into the semantic fields listed in the contract.
    # 3. Use pickup_timestamp hour filtering exactly as described by
    #    hour_window_interpretation.period_examples.
    # 4. Build the partner-zone service-date panel from every observed service day in the
    #    period for that zone, then zero-fill airport_trip_count when an airport has no
    #    airport-linked trip on a panel date.
    # 5. Produce the required outputs in /root/output, including reusable SQL in query_pack.sql.
    # 6. Compute opportunity_score and ranking order from the visible ranking_score definition.
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data_root = Path(args.data)
    output_root = Path(args.output)
    raise SystemExit(
        "Pipeline not implemented yet. Build the analysis so it reads "
        f"{data_root} and writes the required outputs to {output_root}."
    )


if __name__ == "__main__":
    main()
