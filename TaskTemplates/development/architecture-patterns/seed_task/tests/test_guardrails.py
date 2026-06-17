import hashlib
from pathlib import Path

from conftest import VISIBLE_DATA_ROOT, WORKSPACE_ROOT


EXPECTED_HASHES = {
    "gtfs/agency.txt": "b96bd156326ade91ab6a4f2a264716a6ec5321ae7be76eee5935b6300a9c0133",
    "gtfs/calendar.txt": "077cada9ce07a022428ba43ecdb4cf31eeb322951a03111a297d8126859385de",
    "gtfs/calendar_dates.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "gtfs/routes.txt": "99f1a24a692510b968393ee87b703cf03e99913b0e6f5939c64d8c83d2134bd0",
    "gtfs/stops.txt": "d31dff04d8ce633ca877fe0befdf883a10bf6860b57afa38443d0edc57b301ff",
    "gtfs/trips.txt": "40e39471889db0666ceec1a4dc5d79358cd19a7af224b531575593481f1d6740",
    "gtfs/stop_times.txt": "d670ff4785e9217789e39f8b76bdcb94224cecd56157416322cde46f1d32cddf",
    "providers/demo_static.json": "a5c693fc21b4cca7edff81e57519632ad0e4704252cf1a675cb7b2c414dfcb07",
    "providers/city_reference.json": "8aae8266ae3660e1aa545e191421de1ffd3c65326444f1f636b4c9545a2de4a0",
    "seed_queries.json": "29cda15b915d2d32298ca94b7ff0248a655eb2e1cb009addb54d1d413c901435",
    "delivery_contract.yaml": "1119b0de25917d3e9e0c2afceaf4466c9ddde943e2ee154852a741928aebc4f1",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_input_files_unchanged():
    for relative_path, expected_hash in EXPECTED_HASHES.items():
        assert sha256(VISIBLE_DATA_ROOT / relative_path) == expected_hash


def test_existing_entrypoints_preserved():
    assert (WORKSPACE_ROOT / "scripts" / "start_server.sh").exists()
    assert (WORKSPACE_ROOT / "scripts" / "export_snapshot.sh").exists()
    assert (WORKSPACE_ROOT / "scripts" / "provider_audit.sh").exists()
    assert (WORKSPACE_ROOT / "scripts" / "provider_compare.sh").exists()
    assert (WORKSPACE_ROOT / "server.js").exists()


def test_provider_specific_shortcuts_not_added_to_delivery_surfaces():
    forbidden_targets = [
        WORKSPACE_ROOT / "schedule_gateway" / "app.js",
        WORKSPACE_ROOT / "schedule_gateway" / "export_snapshot.js",
        WORKSPACE_ROOT / "schedule_gateway" / "provider_audit.js",
    ]
    for target in forbidden_targets:
        assert "mta_static" not in target.read_text(encoding="utf-8")


def test_visible_gtfs_path_not_hardcoded():
    provider_file = WORKSPACE_ROOT / "schedule_gateway" / "providers" / "mta_static" / "index.js"
    provider_text = provider_file.read_text(encoding="utf-8")
    assert 'path.resolve(__dirname, "../../../data/gtfs")' not in provider_text
    assert 'path.join(__dirname, "../../../data/gtfs")' not in provider_text
