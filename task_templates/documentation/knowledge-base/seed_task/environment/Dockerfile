FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/app
ENV TASK_BUNDLE_ROOT=/app/knowledge-base
ENV TASK_WORKSPACE_ROOT=/app/workspace
ENV TASK_OUTPUT_ROOT=/app/output

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        nodejs \
        npm \
        ripgrep \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest

COPY . /opt/knowledge-base-task-env
COPY skills /app/skills
COPY skills /environment/skills
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /logs/agent/skills

RUN mkdir -p /app/knowledge-base /app/workspace /app/output /app/skills /environment/knowledge-base /environment/workspace /environment/skills /root/.codex/skills /root/.claude/skills /etc/claude-code/.claude/skills /logs/agent/skills /logs/verifier /opt/task-baselines \
    && cp -R /opt/knowledge-base-task-env/knowledge_base/. /app/knowledge-base/ \
    && cp -R /opt/knowledge-base-task-env/workspace/. /app/workspace/ \
    && cp -R /opt/knowledge-base-task-env/knowledge_base/. /environment/knowledge-base/ \
    && cp -R /opt/knowledge-base-task-env/workspace/. /environment/workspace/ \
    && cd /app/knowledge-base && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/knowledge-base.sha256 \
    && chmod -R a+rwX /app/workspace /app/output /logs \
    && chmod 755 /app/workspace/curate_resources.py \
    && chmod 644 /opt/task-baselines/knowledge-base.sha256

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
