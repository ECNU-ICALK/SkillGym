from __future__ import annotations

import csv
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


APP_ROOT = Path("/app")
MISSION_ROOT = Path(os.environ.get("MISSION_PACKET_ROOT", APP_ROOT / "mission_packet"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", APP_ROOT / "output"))
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", APP_ROOT / "workspace"))
DEFAULT_TOOL = APP_ROOT / "skills" / "video-frames" / "scripts" / "frame.sh"
FRAME_TOOL = Path(os.environ.get("MEDIA_PICK_FRAME_TOOL", str(DEFAULT_TOOL)))
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")
_SHIM_DIR: Path | None = None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_requests(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ensure_clean_output() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for name in ("stills", "previews", "sheets"):
        (OUTPUT_ROOT / name).mkdir(parents=True, exist_ok=True)


def resolve_frame_tool() -> str:
    if FRAME_TOOL.exists():
        return str(FRAME_TOOL)
    path_tool = shutil.which("media-pick-frame")
    if path_tool:
        return path_tool
    raise FileNotFoundError(
        f"still helper is unavailable: checked {FRAME_TOOL} and media-pick-frame on PATH"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    global _SHIM_DIR

    if os.path.basename(FFMPEG_BIN) == "ffmpeg":
        return env

    if _SHIM_DIR is None:
        shim_root = Path(tempfile.mkdtemp(prefix="media_ffmpeg_"))
        shim_path = shim_root / "ffmpeg"
        shim_path.symlink_to(Path(FFMPEG_BIN))
        _SHIM_DIR = shim_root

    env["PATH"] = f"{_SHIM_DIR}:{env.get('PATH', '')}"
    return env


def extract_still(tool: str, video_path: Path, locator: str, still_path: Path) -> None:
    command = [tool, str(video_path)] if os.access(tool, os.X_OK) else ["bash", tool, str(video_path)]
    if locator.strip():
        command.extend(shlex.split(locator))
    command.extend(["--out", str(still_path)])
    subprocess.run(command, check=True, env=command_env())


def build_preview(video_path: Path, start_sec: str, duration_sec: str, preview_path: Path) -> None:
    subprocess.run(
        [
            FFMPEG_BIN,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            start_sec,
            "-t",
            duration_sec,
            "-i",
            str(video_path),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(preview_path),
        ],
        check=True,
        env=command_env(),
    )


def fit_still(image_path: Path, cell_width: int, cell_height: int, background: tuple[int, int, int]) -> Image.Image:
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        image.thumbnail((cell_width, cell_height))
        canvas = Image.new("RGB", (cell_width, cell_height), background)
        offset_x = (cell_width - image.width) // 2
        offset_y = (cell_height - image.height) // 2
        canvas.paste(image, (offset_x, offset_y))
        return canvas


CLIP_MANIFEST = load_json(MISSION_ROOT / "clip_manifest.json")
REQUESTS = load_requests(MISSION_ROOT / "shot_requests.csv")
LAYOUT_SPEC = load_json(MISSION_ROOT / "layout_spec.json")
CLIP_LOOKUP = {row["clip_id"]: row for row in CLIP_MANIFEST["clips"]}
REQUEST_LOOKUP = {row["request_id"]: row for row in REQUESTS}


def main() -> None:
    frame_tool = resolve_frame_tool()
    ensure_clean_output()
    background = tuple(LAYOUT_SPEC["sheet_background_rgb"])
    files_created: list[str] = []
    request_records: list[dict[str, object]] = []

    for request in REQUESTS:
        clip = CLIP_LOOKUP[request["clip_id"]]
        video_path = MISSION_ROOT / "videos" / clip["filename"]
        if not video_path.is_file():
            raise FileNotFoundError(f"missing source video for {request['request_id']}: {video_path}")

        still_rel = f"stills/{request['request_id']}.png"
        preview_rel = f"previews/{request['request_id']}.mp4"
        still_path = OUTPUT_ROOT / still_rel
        preview_path = OUTPUT_ROOT / preview_rel

        extract_still(frame_tool, video_path, request["still_locator"], still_path)
        build_preview(video_path, request["preview_start_sec"], request["preview_duration_sec"], preview_path)

        with Image.open(still_path) as image:
            width, height = image.size
        if width != int(clip["width"]) or height != int(clip["height"]):
            raise ValueError(
                f"{request['request_id']} still size {width}x{height} does not match "
                f"{clip['width']}x{clip['height']}"
            )

        files_created.extend([still_rel, preview_rel])
        request_records.append(
            {
                "request_id": request["request_id"],
                "clip_id": request["clip_id"],
                "slot_name": request["slot_name"],
                "still_locator": request["still_locator"],
                "preview_start_sec": float(request["preview_start_sec"]),
                "preview_duration_sec": float(request["preview_duration_sec"]),
                "still_path": still_rel,
                "preview_path": preview_rel,
                "width": width,
                "height": height,
                "sha256": sha256_file(still_path),
            }
        )

    clip_entries = []
    for clip in CLIP_MANIFEST["clips"]:
        clip_requests = [row for row in request_records if row["clip_id"] == clip["clip_id"]]
        sheet_spec = next(row for row in LAYOUT_SPEC["sheets"] if row["clip_id"] == clip["clip_id"])
        canvas = Image.new("RGB", (sheet_spec["canvas_width"], sheet_spec["canvas_height"]), background)
        for index, request_id in enumerate(sheet_spec["request_order"]):
            request_row = next(row for row in clip_requests if row["request_id"] == request_id)
            fitted = fit_still(
                OUTPUT_ROOT / request_row["still_path"],
                sheet_spec["cell_width"],
                sheet_spec["cell_height"],
                background,
            )
            column = index % sheet_spec["columns"]
            grid_row = index // sheet_spec["columns"]
            x = sheet_spec["padding"] + column * (sheet_spec["cell_width"] + sheet_spec["gap"])
            y = sheet_spec["padding"] + grid_row * (sheet_spec["cell_height"] + sheet_spec["gap"])
            canvas.paste(fitted, (x, y))
        sheet_path = OUTPUT_ROOT / sheet_spec["output_file"]
        canvas.save(sheet_path, quality=95)
        files_created.append(sheet_spec["output_file"])

        clip_entries.append(
            {
                "clip_id": clip["clip_id"],
                "source_video": clip["filename"],
                "sheet_path": sheet_spec["output_file"],
                "requests": [
                    {
                        "request_id": row["request_id"],
                        "slot_name": row["slot_name"],
                        "still_locator": row["still_locator"],
                        "preview_start_sec": row["preview_start_sec"],
                        "preview_duration_sec": row["preview_duration_sec"],
                        "still_path": row["still_path"],
                        "preview_path": row["preview_path"],
                        "width": row["width"],
                        "height": row["height"],
                        "sha256": row["sha256"],
                    }
                    for row in clip_requests
                ],
            }
        )

    frame_index = {"clips": clip_entries}
    delivery_report = {
        "bundle_id": CLIP_MANIFEST["bundle_id"],
        "files_created": files_created + ["frame_index.json", "delivery_report.json"],
        "clips_processed": [
            {
                "clip_id": clip["clip_id"],
                "source_video": clip["filename"],
                "request_count": len([row for row in request_records if row["clip_id"] == clip["clip_id"]]),
                "sheet_path": next(row for row in clip_entries if row["clip_id"] == clip["clip_id"])["sheet_path"],
                "status": "pass",
            }
            for clip in CLIP_MANIFEST["clips"]
        ],
        "requests_processed": len(request_records),
        "sheet_count": len(LAYOUT_SPEC["sheets"]),
        "issues": [],
        "notes": [
            f"Generated stills with helper {frame_tool}",
            "Blank still_locator values were handled as valid first-frame requests.",
        ],
    }

    (OUTPUT_ROOT / "frame_index.json").write_text(json.dumps(frame_index, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "delivery_report.json").write_text(
        json.dumps(delivery_report, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
