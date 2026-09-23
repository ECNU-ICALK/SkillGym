FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/environment
ENV TASK_BUNDLE_ROOT=/environment/reference_bundle
ENV TASK_OUTPUT_ROOT=/environment/output
ENV TASK_SKILL_ROOT=/environment/skills/docs-changelog

WORKDIR /environment

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        nodejs \
        npm \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest

COPY . /opt/changelog-task-env
COPY skills /environment/skills
COPY skills /app/skills
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /logs/agent/skills

RUN mkdir -p /environment/reference_bundle /environment/output /environment/skills /app/reference_bundle /app/output /app/skills /root/.codex/skills /root/.claude/skills /etc/claude-code/.claude/skills /logs/agent/skills /logs/verifier /opt/task-baselines \
    && cp -R /opt/changelog-task-env/reference_bundle/. /environment/reference_bundle/ \
    && cp -R /opt/changelog-task-env/reference_bundle/. /app/reference_bundle/ \
    && cd /environment/reference_bundle && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/reference-bundle.sha256 \
    && chmod -R a+rwX /environment/output /app/output /logs \
    && chmod 755 /environment/reference_bundle/workspace/scripts/render_changelog.py \
    && chmod 644 /opt/task-baselines/reference-bundle.sha256

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
