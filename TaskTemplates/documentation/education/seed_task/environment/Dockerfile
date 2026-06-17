FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    nodejs \
    npm \
    python3 \
    python3-ipykernel \
    python3-matplotlib \
    python3-nbclient \
    python3-nbformat \
    python3-pandas \
    python3-pytest \
    python-is-python3 \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/workspace/source_bundle /root/output /root/.codex/skills

COPY source_bundle /root/workspace/source_bundle
COPY skills /root/workspace/source_bundle/skills
COPY skills /root/.codex/skills

RUN find /root/workspace/source_bundle -type f -print0 | sort -z | xargs -0 sha256sum > /opt/education-source-bundle.sha256
