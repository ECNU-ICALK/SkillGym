FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/app
ENV TASK_CAMPAIGN_ROOT=/app/campaign
ENV TASK_WORKSPACE_ROOT=/app/workspace
ENV TASK_OUTPUT_ROOT=/app/output

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        curl \
        findutils \
        git \
        grep \
        procps \
        ripgrep \
        sed \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest \
    pytest-json-ctrf

COPY . /opt/content-creation-task-env
COPY entrypoint.sh /usr/local/bin/content-creation-entrypoint.sh
COPY skills /app/skills
COPY skills /app/workspace/skills
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /logs/agent/skills

RUN mkdir -p /app/campaign /app/workspace /app/output /app/skills /root/.codex/skills /root/.claude/skills /etc/claude-code/.claude/skills /tmp/codex-home/skills /logs/agent/skills /logs/verifier /opt/task-baselines \
    && cp -R /opt/content-creation-task-env/campaign/. /app/campaign/ \
    && cp -R /opt/content-creation-task-env/workspace/. /app/workspace/ \
    && find /app/campaign -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/campaign.sha256 \
    && chmod -R a+rwX /app/workspace /app/output /logs \
    && chmod 755 /app/workspace/build_content_pack.py \
    && chmod 755 /usr/local/bin/content-creation-entrypoint.sh \
    && chmod 644 /opt/task-baselines/campaign.sha256

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/content-creation-entrypoint.sh"]
CMD ["/bin/bash"]
