You need to assemble a pickup bundle from the local mission clips for a review handoff. The workspace already includes the source video registry, a still-request table, a contact-sheet layout spec, and a local build entrypoint. Complete the pickup bundle while preserving the required paths, filenames, and source boundaries.

Input data is available under `/app/mission_packet/`:

- `clip_manifest.json`: the clip registry. It lists every `clip_id`, the source filename, and the expected frame dimensions.
- `shot_requests.csv`: the pickup request table. Each row includes `request_id`, `clip_id`, `still_locator`, `preview_start_sec`, `preview_duration_sec`, and `slot_name`.
- `layout_spec.json`: the contact-sheet naming, clip grouping, request order, and layout settings.
- `videos/launch_pad.mp4`: local source footage for the launch sequence.
- `videos/landing_targeting.mp4`: local source footage for the descent-tracking sequence.
- `videos/landing_touchdown.mp4`: local source footage for the touchdown sequence.
- `/app/workspace/build_packet.py`: the formal local generation entrypoint. Keep this entrypoint usable for the final delivery.

Your tasks

1. Validate that every request maps to a readable source video from `clip_manifest.json`.
2. For each row in `shot_requests.csv`, create one source still at `/app/output/stills/<request_id>.png`.
3. Keep every source still at the source clip's original pixel size. Do not crop, resize, annotate, recolor, or overlay markers.
4. For each row in `shot_requests.csv`, export one preview clip at `/app/output/previews/<request_id>.mp4` using `preview_start_sec` and `preview_duration_sec`.
5. Build one contact sheet per `clip_id` at the path required by `layout_spec.json`. Each sheet must contain only that clip's stills and must follow the request order from the layout spec.
6. Generate `/app/output/frame_index.json` to register each clip, request, and output artifact.
7. Generate `/app/output/delivery_report.json` to summarize the bundle.
8. Keep the local build entrypoint usable so the team can regenerate the same delivery from the current inputs.
9. Clean the delivery for review. Do not leave empty outputs, duplicate variants, review residue, `TODO`, `TBD`, or process commentary in the final outputs.

Output

- Update the formal delivery code and any required supporting files under `/app/workspace/`.
- Keep the build entrypoint compatible with the local still-generation toolchain already present in the environment.
- Create exactly these output paths under `/app/output/`:
  - `stills/`
  - `previews/`
  - `sheets/`
  - `frame_index.json`
  - `delivery_report.json`

`frame_index.json` must use this shape:

```json
{
  "clips": [
    {
      "clip_id": "string",
      "source_video": "string",
      "sheet_path": "string",
      "requests": [
        {
          "request_id": "string",
          "slot_name": "string",
          "still_locator": "string",
          "preview_start_sec": 0.0,
          "preview_duration_sec": 0.0,
          "still_path": "string",
          "preview_path": "string",
          "width": 0,
          "height": 0,
          "sha256": "string"
        }
      ]
    }
  ]
}
```

`delivery_report.json` must include:

```json
{
  "bundle_id": "string",
  "files_created": ["string"],
  "clips_processed": [
    {
      "clip_id": "string",
      "source_video": "string",
      "request_count": 0,
      "sheet_path": "string",
      "status": "string"
    }
  ],
  "requests_processed": 0,
  "sheet_count": 0,
  "issues": ["string"],
  "notes": ["string"]
}
```

Notes

- Do not modify the source videos or the input registry files under `/app/mission_packet/`.
- Blank `still_locator` values are valid requests and still require output files.
- In both JSON outputs, every `source_video` value must match the `filename` field from `clip_manifest.json`.
- Do not change the required output paths or filenames.
- Do not add markdown reports, archives, or extra helper outputs to `/app/output/`.
- Do not modify the tests, validation logic, pinned dependencies, environment configuration, or skill files.
