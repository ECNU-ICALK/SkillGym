You need to deliver a multi-channel publication pack for a climate and energy briefing titled `Renewable Capacity Momentum 2025`. The workspace already includes the editorial brief, channel contract, claim bank, source manifest, voice references, a short video cue sheet, and a local build entrypoint. Complete the pack while keeping the required output paths, data boundaries, and build flow.

Input data is available under `/app/campaign/`:

- `brief/editorial_brief.md`: campaign audience, core message arc, channel goals, and delivery constraints.
- `brief/channel_contract.json`: the formal delivery contract. It defines the required output files, manifest keys, channel limits, banned phrasing, and section labels.
- `data/source_manifest.json`: the approved source ids, labels, and reference links for this pack.
- `data/claim_bank.json`: the supported claims, numbers, source ids, and structured evidence fields for the campaign.
- `data/source_extracts.json`: source-grounded evidence notes that can support defensible wording choices.
- `voice/house_style_samples.md`: local house-style samples for the newsletter voice.
- `voice/channel_voice_notes.md`: channel-specific tone, pacing, and differentiation guidance.
- `assets/video_cue_sheet.md`: the visual progression and on-screen priorities for the short video script.
- `/app/workspace/build_content_pack.py`: the current local build entrypoint. It must remain the formal generation entrypoint for this delivery.

Your tasks

1. Create the final publication pack and write it to `/app/output/`.
2. Produce four channel-specific deliverables from the supplied materials: a newsletter opener, a LinkedIn post, a six-post thread, and a 60-second video script.
3. Follow `channel_contract.json` for the required output files, manifest shape, channel lengths, section labels, and cleanup rules.
4. Keep the campaign theme consistent across all deliverables while making each channel materially different in angle, pacing, proof selection, and closing move.
5. Use only supported numbers, claim ids, organization names, and policy statements from the packaged inputs.
6. Respect the local voice references. The newsletter should sound like a sharp briefing lead rather than a generic summary, and the other channels should stay aligned to their packaged readers.
7. Record which supplied sources support the claims used in each deliverable, and keep those references aligned to the claim ids from `claim_bank.json`.
8. Derive all numbers, claims, and campaign wording from the current packaged inputs on every run so updated local inputs lead to updated outputs.
9. Clean the final delivery so it is ready for review. Do not leave placeholder text, sample copy, review residue, `TODO`, `TBD`, process commentary, or internal-only notes in the output files.
10. Keep the local build entrypoint usable so the team can regenerate the same content pack from the current packaged inputs.

Output

- Update the formal delivery code and any necessary supporting configuration under `/app/workspace/`.
- Create exactly these files under `/app/output/`:
  - `newsletter_intro.md`
  - `linkedin_post.md`
  - `thread.md`
  - `video_script.md`
  - `content_manifest.json`

Channel requirements

- `newsletter_intro.md`
  - One headline and one body
  - Body length: 220 to 320 words

- `linkedin_post.md`
  - One LinkedIn-ready post
  - Length: 120 to 220 words
  - End with a statement, not a question

- `thread.md`
  - Exactly 6 numbered posts in order
  - Each post must be in its own block
  - Each post must stay under 280 characters

- `video_script.md`
  - A 60-second script with 6 sequential scenes
  - Each scene must include `Scene`, `Voiceover`, and `On-screen text`

- `content_manifest.json`
  - Must contain the top-level keys: `campaign_title`, `audience`, `core_messages`, `deliverables`, `sources_used`, `claim_support_notes`
  - `deliverables` must include one entry for each publishable output file and no extra internal rows
  - Each deliverable entry must contain: `file`, `channel`, `primary_angle`, `target_reader`, `claims_used`, `cta`
  - `sources_used` must be a list of source ids from `/app/campaign/data/source_manifest.json`
  - `claim_support_notes` must be a list of items with: `file`, `section`, `claim_id`, `source_id`, `evidence`
  - Use `body` as the section for `newsletter_intro.md` and `linkedin_post.md`
  - Use `post_1` to `post_6` as the sections for `thread.md`
  - Use `scene_1` to `scene_6` as the sections for `video_script.md`

Notes

- Do not modify the input data, brief files, voice references, or cue sheets under `/app/campaign/`.
- Do not change the required output paths or filenames.
- Do not modify the tests, validation logic, pinned dependencies, environment configuration, or skill files.
- Do not depend on internet access at solve time.
