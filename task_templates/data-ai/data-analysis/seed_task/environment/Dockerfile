FROM ubuntu:24.04

WORKDIR /root

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python-is-python3 \
        python3-pandas \
        python3-numpy \
        python3-scipy \
        python3-pytest \
        nodejs \
        npm \
        sqlite3 \
        tini \
        ripgrep \
    && rm -rf /var/lib/apt/lists/*

COPY data /root/data
COPY workspace /root/workspace
COPY skills /root/workspace/skills
COPY skills /root/.codex/skills

RUN mkdir -p /root/output \
    && chmod +x /root/workspace/run_airport_partner_analysis.py
