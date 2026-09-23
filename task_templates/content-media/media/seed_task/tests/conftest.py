from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageChops, ImageStat


BASE_DIR = Path(__file__).resolve().parent.parent
APP_ROOT = Path("/app")
FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"
BASELINE_SHA_PATH = FIXTURES_ROOT / "mission_packet.sha256"


def _default_path(app_path: Path, repo_path: Path) -> Path:
    return app_path if app_path.exists() else repo_path


MISSION_ROOT = Path(
    os.environ.get(
        "TASK_MISSION_ROOT",
        _default_path(APP_ROOT / "mission_packet", BASE_DIR / "environment" / "mission_packet"),
    )
)
WORKSPACE_ROOT = Path(
    os.environ.get(
        "TASK_WORKSPACE_ROOT",
        _default_path(APP_ROOT / "workspace", BASE_DIR / "environment" / "workspace"),
    )
)
OUTPUT_ROOT = Path(
    os.environ.get(
        "TASK_OUTPUT_ROOT",
        _default_path(APP_ROOT / "output", BASE_DIR / ".tmp_test_output"),
    )
)


def ffmpeg_bin() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def clip_manifest() -> dict:
    return json.loads((MISSION_ROOT / "clip_manifest.json").read_text(encoding="utf-8"))


def shot_requests() -> list[dict[str, str]]:
    with (MISSION_ROOT / "shot_requests.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def layout_spec() -> dict:
    return json.loads((MISSION_ROOT / "layout_spec.json").read_text(encoding="utf-8"))


def run_build(
    *,
    mission_root: Path | None = None,
    workspace_root: Path | None = None,
    output_root: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    repo_tool = BASE_DIR / "environment" / "skills" / "video-frames" / "scripts" / "frame.sh"
    ffmpeg_path = ffmpeg_bin()
    if extra_env:
        env.update(extra_env)
    if repo_tool.exists() and not env.get("MEDIA_PICK_FRAME_TOOL") and not (APP_ROOT / "skills").exists():
        env["MEDIA_PICK_FRAME_TOOL"] = str(repo_tool)
    env["FFMPEG_BIN"] = ffmpeg_path
    env["PATH"] = f"{Path(ffmpeg_path).parent}:{env['PATH']}"
    env["MISSION_PACKET_ROOT"] = str(mission_root or MISSION_ROOT)
    env["TASK_OUTPUT_ROOT"] = str(output_root or OUTPUT_ROOT)
    env["WORKSPACE_ROOT"] = str(workspace_root or WORKSPACE_ROOT)
    return subprocess.run(
        ["python3", str((workspace_root or WORKSPACE_ROOT) / "build_packet.py")],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def parse_locator(locator: str) -> tuple[str | None, int | None]:
    locator = locator.strip()
    if not locator:
        return None, None
    parts = locator.split()
    if parts[:1] == ["--time"] and len(parts) == 2:
        return parts[1], None
    if parts[:1] == ["--index"] and len(parts) == 2:
        return None, int(parts[1])
    raise ValueError(f"unsupported locator: {locator}")


def extract_expected_still(video_path: Path, locator: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    time_value, index_value = parse_locator(locator)
    command = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y"]
    if time_value is not None:
        command.extend(["-ss", time_value])
    command.extend(["-i", str(video_path)])
    if index_value is not None:
        command.extend(["-vf", f"select=eq(n\\,{index_value})"])
    else:
        command.extend(["-vf", "select=eq(n\\,0)" if time_value is None else "null"])
    command.extend(["-vframes", "1", str(output_path)])
    subprocess.run(command, check=True)


def extract_first_frame(video_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path), "-frames:v", "1", str(output_path)],
        check=True,
    )


def image_rmse(left: Path, right: Path) -> float:
    with Image.open(left).convert("RGB") as left_image, Image.open(right).convert("RGB") as right_image:
        if left_image.size != right_image.size:
            return float("inf")
        diff = ImageChops.difference(left_image, right_image)
        stat = ImageStat.Stat(diff)
        return sum((value ** 2 for value in stat.rms)) ** 0.5


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_expected_sheet(sheet_spec: dict, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    background = tuple(layout_spec()["sheet_background_rgb"])
    canvas = Image.new("RGB", (sheet_spec["canvas_width"], sheet_spec["canvas_height"]), background)
    request_lookup = {row["request_id"]: row for row in shot_requests()}

    for index, request_id in enumerate(sheet_spec["request_order"]):
        request = request_lookup[request_id]
        still_path = OUTPUT_ROOT / "stills" / f"{request_id}.png"
        with Image.open(still_path).convert("RGB") as image:
            image.thumbnail((sheet_spec["cell_width"], sheet_spec["cell_height"]))
            fitted = Image.new("RGB", (sheet_spec["cell_width"], sheet_spec["cell_height"]), background)
            offset_x = (sheet_spec["cell_width"] - image.width) // 2
            offset_y = (sheet_spec["cell_height"] - image.height) // 2
            fitted.paste(image, (offset_x, offset_y))
        column = index % sheet_spec["columns"]
        row = index // sheet_spec["columns"]
        x = sheet_spec["padding"] + column * (sheet_spec["cell_width"] + sheet_spec["gap"])
        y = sheet_spec["padding"] + row * (sheet_spec["cell_height"] + sheet_spec["gap"])
        canvas.paste(fitted, (x, y))

    canvas.save(destination, quality=95)
    return destination


def output_inventory() -> set[str]:
    items: set[str] = set()
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file():
            items.add(path.relative_to(OUTPUT_ROOT).as_posix())
    return items


def current_hash_lines(root: Path) -> str:
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    return "\n".join(lines) + "\n"


def output_json(name: str) -> dict:
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))
