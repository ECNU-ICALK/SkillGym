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

COPY . /tmp/environment-context

RUN mkdir -p /root/data /root/output /root/.codex/skills /home/user/.codex/skills /logs/agent/skills \
    && cp -R /tmp/environment-context/data/. /root/data/ \
    && if [ -d /tmp/environment-context/skills ]; then \
         cp -R /tmp/environment-context/skills/. /root/.codex/skills/; \
         cp -R /tmp/environment-context/skills/. /home/user/.codex/skills/; \
         cp -R /tmp/environment-context/skills/. /logs/agent/skills/; \
       fi \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/lab-tools-data.sha256 \
    && if [ -d /root/.codex/skills/jupyter-notebook ]; then \
         find /root/.codex/skills/jupyter-notebook -type f -print0 | sort -z | xargs -0 sha256sum > /opt/lab-tools-skill.sha256; \
       fi
