FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/environment
ENV TASK_REFERENCE_ROOT=/environment/reference_bundle
ENV TASK_WORKSPACE_ROOT=/environment/workspace
ENV TASK_OUTPUT_ROOT=/environment/output

WORKDIR /environment

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

COPY . /opt/technical-docs-task-env
COPY skills /app/skills
COPY skills /environment/skills
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /logs/agent/skills

RUN mkdir -p /app/reference_bundle /app/workspace /app/output /app/skills /environment/reference_bundle /environment/workspace /environment/output /environment/skills /root/.codex/skills /root/.claude/skills /etc/claude-code/.claude/skills /logs/agent/skills /logs/verifier /opt/task-baselines \
    && cp -R /opt/technical-docs-task-env/reference_bundle/. /app/reference_bundle/ \
    && cp -R /opt/technical-docs-task-env/workspace/. /app/workspace/ \
    && cp -R /opt/technical-docs-task-env/reference_bundle/. /environment/reference_bundle/ \
    && cp -R /opt/technical-docs-task-env/workspace/. /environment/workspace/ \
    && cd /environment/reference_bundle && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/reference-bundle.sha256 \
    && chmod -R a+rwX /app/workspace /app/output /environment/workspace /environment/output /logs \
    && chmod 755 /app/workspace/build_reference.py /environment/workspace/build_reference.py \
    && chmod 644 /opt/task-baselines/reference-bundle.sha256

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
