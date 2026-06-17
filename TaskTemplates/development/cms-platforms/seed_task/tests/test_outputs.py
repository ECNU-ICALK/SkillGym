import os
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from oracle import expected_summary, feed_matches_contract, invalid_publish_candidates, summary_matches_contract


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:3000")


def request_json(method, path, body=None, token=None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"JWT {token}"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        parsed = json.loads(payload) if payload else None
        return exc.code, parsed


def extract_feed_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("items", [])
    return []


def wait_for_server():
    for _ in range(120):
        try:
            with urllib.request.urlopen(BASE_URL + "/api/highlight-lanes/feed", timeout=5) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError("server did not become ready")


def login(email, password):
    status, payload = request_json("POST", "/api/users/login", {"email": email, "password": password})
    if status != 200 or "token" not in payload:
        raise AssertionError(f"login failed for {email}: {status} {payload}")
    return payload["token"]


def get_doc(collection, where, token, extra_query=""):
    query = urllib.parse.quote(json.dumps(where))
    path = f"/api/{collection}?where={query}"
    if extra_query:
        path += f"&{extra_query}"
    status, payload = request_json("GET", path, token=token)
    if status != 200:
        raise AssertionError(f"{collection} lookup failed: {status} {payload}")
    docs = payload.get("docs", [])
    if len(docs) != 1:
        raise AssertionError(f"expected one {collection} doc for {where}, got {len(docs)}")
    return docs[0]


def verify_initial_state(failures):
    summary_path = WORKSPACE_ROOT / "output" / "seed-summary.json"
    if not summary_path.exists():
        failures.append("summary.json missing after reseed")
    else:
        actual_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        matches, reason = summary_matches_contract(actual_summary, WORKSPACE_ROOT)
        if not matches:
            failures.append(f"summary mismatch: {reason}; actual={actual_summary}; expected={expected_summary(WORKSPACE_ROOT)}")

    status, payload = request_json("GET", "/api/highlight-lanes/feed")
    if status != 200:
        failures.append(f"feed endpoint failed: {status} {payload}")
        return

    items = extract_feed_items(payload)
    matches, reason = feed_matches_contract(items, WORKSPACE_ROOT)
    if not matches:
        failures.append(f"feed payload does not match expected published highlights: {reason}")

    status, photo_payload = request_json("GET", "/api/highlight-lanes/feed?department=photographs")
    if status != 200:
        failures.append(f"department filter failed: {status}")
    else:
        photo_items = extract_feed_items(photo_payload)
        if len(photo_items) != 1:
            failures.append(f"department filter expected 1 photograph item, got {len(photo_items)}")
        elif photo_items[0].get("objectURL") != "https://www.metmuseum.org/art/collection/search/267766":
            failures.append("department filter returned the wrong photograph item")

    status, family_payload = request_json("GET", "/api/highlight-lanes/feed?audience=families")
    if status != 200:
        failures.append(f"audience filter failed: {status}")
    else:
        family_items = extract_feed_items(family_payload)
        if [item["lane"] for item in family_items] != ["Cross-Cultural Forms", "Cross-Cultural Forms"]:
            failures.append("audience filter returned unexpected lanes")

    invalid_rows = invalid_publish_candidates(WORKSPACE_ROOT)
    invalid_object_urls = {row["objectURL"] for row in invalid_rows}
    leaked = [item["objectURL"] for item in items if item["objectURL"] in invalid_object_urls]
    if leaked:
        failures.append(f"feed leaked ineligible artworks: {leaked}")

    status, highlights_payload = request_json("GET", "/api/highlights?depth=1&limit=100")
    if status in (401, 403):
        pass
    elif status != 200:
        failures.append(f"anonymous highlights list failed: {status} {highlights_payload}")
    else:
        leaked_highlights = []
        for doc in highlights_payload.get("docs", []):
            artwork = doc.get("artwork")
            if isinstance(artwork, dict) and artwork.get("objectURL") in invalid_object_urls:
                leaked_highlights.append(artwork.get("objectURL"))
        if leaked_highlights:
            failures.append(f"anonymous highlights leaked ineligible published docs: {sorted(leaked_highlights)}")


def verify_role_boundaries(failures):
    admin_token = login("admin@metfeed.local", "AdminPass123!")
    editor_token = login("editor@metfeed.local", "EditorPass123!")
    assistant_editor_token = login("assistant.editor@metfeed.local", "AssistantEditorPass123!")
    curator_token = login("curator@metfeed.local", "CuratorPass123!")
    assistant_editor_user = get_doc("users", {"email": {"equals": "assistant.editor@metfeed.local"}}, admin_token)
    artwork = get_doc("artworks", {"objectID": {"equals": 283170}}, curator_token)
    valid_lane = get_doc("highlight-lanes", {"laneKey": {"equals": "costume-and-performance"}}, curator_token)
    invalid_lane = get_doc("highlight-lanes", {"laneKey": {"equals": "cross-cultural-forms"}}, curator_token)
    suffix = int(time.time())
    slug = f"verifier-weekend-{suffix}"
    editor_escalation_slug = f"editor-escalation-{suffix}"

    status, escalation_payload = request_json(
        "POST",
        "/api/highlights",
        {
            "headline": "Editor Escalation Check",
            "slug": editor_escalation_slug,
            "lane": valid_lane["id"],
            "artwork": artwork["id"],
            "sortOrder": 1,
            "_status": "published",
        },
        token=editor_token,
    )
    if status in (200, 201):
        query = urllib.parse.quote(json.dumps({"slug": {"equals": editor_escalation_slug}}))
        status_after_create, payload_after_create = request_json(
            "GET",
            f"/api/highlights?where={query}&depth=0&limit=2",
            token=curator_token,
        )
        if status_after_create != 200:
            failures.append(
                f"could not inspect editor escalation highlight: {status_after_create} {payload_after_create}"
            )
        else:
            docs = payload_after_create.get("docs", []) if isinstance(payload_after_create, dict) else []
            if len(docs) == 1:
                persisted_doc = docs[0]
                if persisted_doc.get("_status") == "published":
                    failures.append("editor was able to publish a highlight while creating it")
                if persisted_doc.get("sortOrder") == 1:
                    failures.append("editor was able to keep a custom sortOrder while creating a draft highlight")

            status, weekend_payload = request_json("GET", "/api/highlight-lanes/feed?audience=weekend")
            if status != 200:
                failures.append(f"weekend feed unavailable after editor escalation create: {status} {weekend_payload}")
            else:
                weekend_slugs = [item["slug"] for item in extract_feed_items(weekend_payload)]
                if editor_escalation_slug in weekend_slugs:
                    failures.append("editor-created escalation highlight leaked into the public weekend feed")

    status, payload = request_json(
        "POST",
        "/api/highlights",
        {
            "headline": "Verifier Weekend Highlight",
            "slug": slug,
            "lane": valid_lane["id"],
            "artwork": artwork["id"],
            "sortOrder": 15,
        },
        token=editor_token,
    )
    if status not in (200, 201):
        failures.append(f"editor could not create draft highlight: {status} {payload}")
        return

    created_doc = get_doc("highlights", {"slug": {"equals": slug}}, curator_token)
    doc_id = str(created_doc["id"])
    assistant_slug = f"assistant-weekend-{suffix}"
    status, assistant_payload = request_json(
        "POST",
        "/api/highlights",
        {
            "headline": "Assistant Weekend Highlight",
            "slug": assistant_slug,
            "lane": valid_lane["id"],
            "artwork": artwork["id"],
            "sortOrder": 25,
        },
        token=assistant_editor_token,
    )
    if status not in (200, 201):
        failures.append(f"assistant editor could not create draft highlight: {status} {assistant_payload}")
        return

    assistant_doc = get_doc("highlights", {"slug": {"equals": assistant_slug}}, curator_token)
    assistant_doc_id = str(assistant_doc["id"])

    owner_spoof_slug = f"owner-spoof-{suffix}"
    owner_spoof_doc = None
    status, owner_spoof_payload = request_json(
        "POST",
        "/api/highlights",
        {
            "headline": "Owner Spoof Check",
            "slug": owner_spoof_slug,
            "lane": valid_lane["id"],
            "artwork": artwork["id"],
            "owner": assistant_editor_user["id"],
            "draftOwner": assistant_editor_user["id"],
        },
        token=editor_token,
    )
    if status not in (200, 201):
        failures.append(f"editor could not create owner spoof draft highlight: {status} {owner_spoof_payload}")
    else:
        owner_spoof_doc = get_doc("highlights", {"slug": {"equals": owner_spoof_slug}}, curator_token)

    status, editor_highlights = request_json("GET", "/api/highlights?depth=0&limit=50", token=editor_token)
    if status != 200:
        failures.append(f"editor could not list highlights: {status} {editor_highlights}")
    else:
        editor_ids = {doc["id"] for doc in editor_highlights.get("docs", [])}
        if created_doc["id"] not in editor_ids:
            failures.append("editor cannot see their own draft highlight")
        if owner_spoof_doc is not None and owner_spoof_doc["id"] not in editor_ids:
            failures.append("editor lost visibility of a draft they created after attempting to spoof ownership")
        if assistant_doc["id"] in editor_ids:
            failures.append("editor can see another editor's draft highlight")

    status, assistant_highlights = request_json("GET", "/api/highlights?depth=0&limit=50", token=assistant_editor_token)
    if status != 200:
        failures.append(f"assistant editor could not list highlights: {status} {assistant_highlights}")
    else:
        assistant_ids = {doc["id"] for doc in assistant_highlights.get("docs", [])}
        if assistant_doc["id"] not in assistant_ids:
            failures.append("assistant editor cannot see their own draft highlight")
        if created_doc["id"] in assistant_ids:
            failures.append("assistant editor can see another editor's draft highlight")
        if owner_spoof_doc is not None and owner_spoof_doc["id"] in assistant_ids:
            failures.append("assistant editor gained visibility of another editor's new draft through ownership spoofing")

    status, _payload = request_json(
        "PATCH",
        f"/api/highlights/{assistant_doc_id}",
        {"headline": "Editor should not edit another editor draft"},
        token=editor_token,
    )
    if 200 <= status < 300:
        failures.append("editor was able to modify another editor's draft highlight")

    status, delete_payload = request_json(
        "DELETE",
        f"/api/highlights/{doc_id}",
        token=editor_token,
    )
    if 200 <= status < 300:
        failures.append("editor was able to delete their own draft highlight")
    else:
        try:
            get_doc("highlights", {"slug": {"equals": slug}}, curator_token)
        except AssertionError as exc:
            failures.append(f"editor delete attempt removed their own draft highlight: {exc}")

    status, _payload = request_json(
        "PATCH",
        f"/api/highlights/{doc_id}",
        {"_status": "published", "sortOrder": 15},
        token=editor_token,
    )
    persisted_doc_after_editor = get_doc("highlights", {"slug": {"equals": slug}}, curator_token)
    if (
        persisted_doc_after_editor.get("_status") == "published"
        or persisted_doc_after_editor.get("sortOrder") != created_doc.get("sortOrder")
    ):
        failures.append("editor was able to publish or reorder a highlight")

    status, payload = request_json(
        "PATCH",
        f"/api/highlights/{doc_id}",
        {"_status": "published", "sortOrder": 15},
        token=curator_token,
    )
    if status != 200:
        failures.append(f"curator could not publish ready draft highlight: {status} {payload}")
        return

    status, payload = request_json("GET", "/api/highlight-lanes/feed?audience=weekend")
    if status != 200:
        failures.append("weekend feed unavailable after curator publish")
    else:
        slugs = [item["slug"] for item in extract_feed_items(payload)]
        if slug not in slugs:
            failures.append("curator publish did not update the public weekend feed")

    status, _payload = request_json(
        "PATCH",
        f"/api/highlights/{doc_id}",
        {"lane": invalid_lane["id"]},
        token=curator_token,
    )
    if 200 <= status < 300:
        moved_status, moved_doc = request_json("GET", f"/api/highlights/{doc_id}?depth=1", token=curator_token)
        if moved_status != 200:
            failures.append(f"could not inspect highlight after invalid lane move: {moved_status} {moved_doc}")
        else:
            weekend_status, weekend_payload = request_json("GET", "/api/highlight-lanes/feed?audience=weekend")
            if weekend_status != 200:
                failures.append(f"could not inspect public feed after invalid lane move: {weekend_status} {weekend_payload}")
            else:
                weekend_slugs = [item["slug"] for item in extract_feed_items(weekend_payload)]
                if moved_doc.get("_status") == "published" and slug in weekend_slugs:
                    failures.append("curator was able to move a highlight into an invalid lane")

    protected_artwork = get_doc("artworks", {"objectID": {"equals": 436532}}, curator_token)
    artwork_id = str(protected_artwork["id"])
    original_title = protected_artwork["title"]

    status, _payload = request_json(
        "PATCH",
        f"/api/artworks/{artwork_id}",
        {"title": "Editor should not update catalog titles"},
        token=editor_token,
    )
    if 200 <= status < 300:
        failures.append("editor was able to modify an artwork record")

    status, payload = request_json(
        "PATCH",
        f"/api/artworks/{artwork_id}",
        {"title": f"{original_title} (curator check)"},
        token=curator_token,
    )
    if status != 200:
        failures.append(f"curator could not modify an artwork record: {status} {payload}")
    else:
        restore_status, restore_payload = request_json(
            "PATCH",
            f"/api/artworks/{artwork_id}",
            {"title": original_title},
            token=curator_token,
        )
    if restore_status != 200:
        failures.append(f"curator could not restore artwork title: {restore_status} {restore_payload}")

    public_access_artwork = get_doc("artworks", {"objectID": {"equals": 267766}}, curator_token)
    public_access_artwork_id = str(public_access_artwork["id"])
    original_primary_image = public_access_artwork.get("primaryImage", "")
    public_access_object_url = public_access_artwork.get("objectURL")

    status, payload = request_json(
        "PATCH",
        f"/api/artworks/{public_access_artwork_id}",
        {"primaryImage": ""},
        token=curator_token,
    )
    if status != 200:
        failures.append(f"curator could not remove the public image from a published artwork: {status} {payload}")
    else:
        highlight_query = urllib.parse.quote(json.dumps({"artwork": {"equals": public_access_artwork["id"]}}))
        status, anonymous_highlights = request_json("GET", f"/api/highlights?where={highlight_query}&depth=1")
        if status in (401, 403):
            pass
        elif status != 200:
            failures.append(f"anonymous highlight read failed after artwork update: {status} {anonymous_highlights}")
        else:
            leaked_docs = anonymous_highlights.get("docs", []) if isinstance(anonymous_highlights, dict) else []
            leaked_urls = [
                doc.get("artwork", {}).get("objectURL")
                for doc in leaked_docs
                if isinstance(doc.get("artwork"), dict)
            ]
            if public_access_object_url in leaked_urls:
                failures.append("anonymous highlight read still exposed a highlight after the artwork became ineligible")

        status, hidden_feed = request_json("GET", "/api/highlight-lanes/feed?department=photographs")
        if status != 200:
            failures.append(f"feed check failed after artwork update: {status} {hidden_feed}")
        else:
            hidden_items = extract_feed_items(hidden_feed)
            if any(item.get("objectURL") == public_access_object_url for item in hidden_items):
                failures.append("public feed still exposed a highlight after the artwork became ineligible")

        restore_status, restore_payload = request_json(
            "PATCH",
            f"/api/artworks/{public_access_artwork_id}",
            {"primaryImage": original_primary_image},
            token=curator_token,
        )
        if restore_status != 200:
            failures.append(
                f"curator could not restore the published artwork image after access check: {restore_status} {restore_payload}"
            )

    temp_suffix = int(time.time())
    temp_user_body = {
        "displayName": "Verifier Temp User",
        "email": f"verifier-temp-{temp_suffix}@metfeed.local",
        "password": "VerifierPass123!",
        "role": "editor",
    }

    status, _payload = request_json("POST", "/api/users", temp_user_body, token=editor_token)
    if 200 <= status < 300:
        failures.append("editor was able to create a user")

    status, _payload = request_json("POST", "/api/users", temp_user_body, token=curator_token)
    if 200 <= status < 300:
        failures.append("curator was able to create a user")

    status, payload = request_json("POST", "/api/users", temp_user_body, token=admin_token)
    if status not in (200, 201):
        failures.append(f"admin could not create a user: {status} {payload}")


def main():
    wait_for_server()
    failures = []
    verify_initial_state(failures)
    verify_role_boundaries(failures)

    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)

    print("PASS")


if __name__ == "__main__":
    main()
