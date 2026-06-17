from __future__ import annotations

from collections import Counter
from typing import Any

from .catalog import load_classifiers, load_license_index, load_licenses


def snapshot(top_roots_limit: int = 5) -> dict[str, Any]:
    licenses = load_licenses()
    classifiers = load_classifiers()
    roots = [value.split(" :: ", 1)[0] for value in classifiers]
    counts = Counter(roots)
    top_roots = [
        {"root": root, "count": count}
        for root, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_roots_limit]
    ]
    return {
        "license_count": len(licenses),
        "osi_approved_count": sum(1 for row in licenses if row.get("isOsiApproved")),
        "deprecated_license_count": sum(1 for row in licenses if row.get("isDeprecatedLicenseId")),
        "classifier_count": len(classifiers),
        "top_classifier_roots": top_roots,
    }


def license_lookup(license_id: str) -> dict[str, Any]:
    item = load_license_index()[license_id]
    return {
        "id": item["licenseId"],
        "name": item["name"],
        "osi_approved": bool(item.get("isOsiApproved")),
        "deprecated": bool(item.get("isDeprecatedLicenseId")),
        "reference_count": len(item.get("seeAlso", [])),
    }


def classifier_prefix(prefix: str, limit: int | None = None) -> dict[str, Any]:
    matches = [value for value in load_classifiers() if value.startswith(prefix)]
    if limit is not None:
        matches = matches[:limit]
    return {
        "prefix": prefix,
        "matches": matches,
        "match_count": len(matches),
    }
