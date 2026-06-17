import csv
import json
from pathlib import Path


def load_fixture_state(workspace_root: Path):
    data_root = workspace_root.parent / "data"
    seed_rows = list(csv.DictReader((data_root / "met_objects_seed.csv").read_text(encoding="utf-8").splitlines()))
    details = [json.loads(line) for line in (data_root / "met_object_details.ndjson").read_text(encoding="utf-8").splitlines() if line.strip()]
    details_by_id = {str(item["objectID"]): item for item in details}
    lanes = json.loads((data_root / "audience_lanes.json").read_text(encoding="utf-8"))["lanes"]
    lanes_by_key = {item["key"]: item for item in lanes}
    return seed_rows, details_by_id, lanes_by_key


def row_ready_for_highlight(row, details_by_id):
    details = details_by_id[row["objectID"]]
    return bool(details["isPublicDomain"]) and bool((details["primaryImageSmall"] or "").strip())


def row_matches_lane_departments(row, lanes_by_key):
    lane = lanes_by_key[row["laneKey"]]
    return row["departmentSlug"] in set(lane["departmentSlugs"])


def row_is_public_feed_eligible(row, details_by_id, lanes_by_key):
    return (
        row["targetState"] == "publish"
        and row_ready_for_highlight(row, details_by_id)
        and row_matches_lane_departments(row, lanes_by_key)
    )


def expected_summary(workspace_root: Path):
    seed_rows, details_by_id, lanes_by_key = load_fixture_state(workspace_root)
    departments = {row["departmentSlug"] for row in seed_rows}
    artists = {row["artistSlug"] for row in seed_rows}
    published = [row for row in seed_rows if row_is_public_feed_eligible(row, details_by_id, lanes_by_key)]
    return {
        "departments": len(departments),
        "artists": len(artists),
        "artworks": len(seed_rows),
        "highlightLanes": len(lanes_by_key),
        "publishedHighlights": len(published),
    }


def summary_matches_contract(actual_summary, workspace_root: Path):
    expected = expected_summary(workspace_root)

    if not isinstance(actual_summary, dict):
        return False, f"summary is not an object: {actual_summary!r}"

    for key in ["artists", "artworks", "highlightLanes"]:
        if actual_summary.get(key) != expected[key]:
            return False, f"{key} mismatch: {actual_summary.get(key)} != {expected[key]}"

    published_highlights = actual_summary.get("publishedHighlights")
    public_feed_items = actual_summary.get("publicFeedItems")
    if published_highlights != expected["publishedHighlights"] and public_feed_items != expected["publishedHighlights"]:
        return (
            False,
            "published summary mismatch: "
            f"publishedHighlights={published_highlights!r}, publicFeedItems={public_feed_items!r}, "
            f"expected={expected['publishedHighlights']}",
        )

    actual_departments = actual_summary.get("departments")
    if not isinstance(actual_departments, int):
        return False, f"departments is not an integer: {actual_departments!r}"
    if actual_departments < expected["departments"]:
        return False, f"departments mismatch: {actual_departments} < {expected['departments']}"

    return True, "ok"


def expected_feed(workspace_root: Path):
    seed_rows, details_by_id, lanes_by_key = load_fixture_state(workspace_root)
    items = []
    for row in seed_rows:
        if not row_is_public_feed_eligible(row, details_by_id, lanes_by_key):
            continue
        lane = lanes_by_key[row["laneKey"]]
        details = details_by_id[row["objectID"]]
        items.append(
            {
                "_laneKey": row["laneKey"],
                "lane": lane["title"],
                "title": row["editorialTitle"],
                "slug": f"{row['laneKey']}-{row['objectID']}",
                "artistName": row["artistName"],
                "department": row["departmentName"],
                "objectDate": details["objectDate"],
                "primaryImage": details["primaryImageSmall"],
                "objectURL": details["objectURL"],
                "sortOrder": int(row["sortOrder"]),
            }
        )

    items.sort(key=lambda item: (item["_laneKey"], item["sortOrder"], item["slug"]))
    return [{k: v for k, v in item.items() if k != "_laneKey"} for item in items]


def expected_feed_contract(workspace_root: Path):
    seed_rows, details_by_id, lanes_by_key = load_fixture_state(workspace_root)
    items = []
    for row in seed_rows:
        if not row_is_public_feed_eligible(row, details_by_id, lanes_by_key):
            continue
        lane = lanes_by_key[row["laneKey"]]
        details = details_by_id[row["objectID"]]
        items.append(
            {
                "_laneKey": row["laneKey"],
                "lane": lane["title"],
                "editorialTitle": row["editorialTitle"],
                "artworkTitle": details["title"],
                "slugPrefix": f"{row['laneKey']}-{row['objectID']}",
                "artistName": row["artistName"],
                "department": row["departmentName"],
                "departmentSlug": row["departmentSlug"],
                "objectDate": details["objectDate"],
                "primaryImage": details["primaryImageSmall"],
                "objectURL": details["objectURL"],
                "sortOrder": int(row["sortOrder"]),
            }
        )

    items.sort(key=lambda item: (item["_laneKey"], item["sortOrder"], item["slugPrefix"]))
    return [{k: v for k, v in item.items() if k != "_laneKey"} for item in items]


def feed_matches_contract(actual_items, workspace_root: Path):
    expected_items = expected_feed_contract(workspace_root)
    if len(actual_items) != len(expected_items):
        return False, f"expected {len(expected_items)} items, got {len(actual_items)}"

    for actual, expected in zip(actual_items, expected_items):
        if actual.get("lane") != expected["lane"]:
            return False, f"lane mismatch for {expected['slugPrefix']}: {actual.get('lane')} != {expected['lane']}"
        if actual.get("artistName") != expected["artistName"]:
            return False, f"artist mismatch for {expected['slugPrefix']}"
        if actual.get("department") != expected["department"]:
            return False, f"department mismatch for {expected['slugPrefix']}"
        if actual.get("objectDate") != expected["objectDate"]:
            return False, f"objectDate mismatch for {expected['slugPrefix']}"
        if actual.get("primaryImage") != expected["primaryImage"]:
            return False, f"primaryImage mismatch for {expected['slugPrefix']}"
        if actual.get("objectURL") != expected["objectURL"]:
            return False, f"objectURL mismatch for {expected['slugPrefix']}"
        if actual.get("sortOrder") != expected["sortOrder"]:
            return False, f"sortOrder mismatch for {expected['slugPrefix']}"

        title = actual.get("title")
        if title not in {expected["editorialTitle"], expected["artworkTitle"]}:
            return False, f"title mismatch for {expected['slugPrefix']}: {title}"

        slug = actual.get("slug", "")
        if not isinstance(slug, str) or not slug.startswith(expected["slugPrefix"]):
            return False, f"slug mismatch for {expected['slugPrefix']}: {slug}"

    return True, "ok"


def normalize_feed_payload(payload):
    if isinstance(payload, dict):
        return {
            "total": payload.get("total"),
            "items": payload.get("items", []),
        }

    if isinstance(payload, list):
        return {
            "total": len(payload),
            "items": payload,
        }

    return {
        "total": None,
        "items": [],
    }


def ready_draft_candidate(workspace_root: Path):
    seed_rows, _details_by_id, _lanes_by_key = load_fixture_state(workspace_root)
    for row in seed_rows:
        if row["readyForHighlight"] == "true" and row["targetState"] == "draft":
            return row
    raise RuntimeError("No ready draft candidate found.")


def invalid_publish_candidates(workspace_root: Path):
    seed_rows, details_by_id, lanes_by_key = load_fixture_state(workspace_root)
    return [
        row
        for row in seed_rows
        if row["targetState"] == "publish" and not row_is_public_feed_eligible(row, details_by_id, lanes_by_key)
    ]
