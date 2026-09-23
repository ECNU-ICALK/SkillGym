FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        jq \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pillow pytest imageio-ffmpeg

WORKDIR /app

COPY mission_packet /app/mission_packet
COPY workspace /app/workspace
COPY skills /tmp/codex-home/skills
COPY skills /root/.codex/skills
COPY skills /app/skills

RUN mkdir -p /app/output /app/workspace /tmp/codex-home/skills \
    && cat >/usr/local/bin/media-pick-frame <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec bash /app/skills/video-frames/scripts/frame.sh "$@"
EOF
RUN chmod +x /usr/local/bin/media-pick-frame

ENV MEDIA_PICK_FRAME_TOOL=/usr/local/bin/media-pick-frame
