FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/app
ENV TASK_BUNDLE_ROOT=/app/release-watch
ENV TASK_WORKSPACE_ROOT=/app/workspace
ENV TASK_OUTPUT_ROOT=/app/output
ENV BLOGWATCHER_VERSION=0.0.3

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        ripgrep \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest

COPY release_watch /opt/productivity-tools-task-env/release_watch
COPY workspace /opt/productivity-tools-task-env/workspace
COPY setup_environment.py /opt/productivity-tools-task-env/setup_environment.py
COPY skills /opt/productivity-tools-task-env/skills
COPY skills /root/.agents/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills
COPY entrypoint.sh /usr/local/bin/productivity-tools-entrypoint.sh

RUN curl -fsSL -o /tmp/blogwatcher.tar.gz \
        https://github.com/Hyaxia/blogwatcher/releases/download/v0.0.3/blogwatcher_0.0.3_linux_amd64.tar.gz \
    && tar -xzf /tmp/blogwatcher.tar.gz -C /usr/local/bin blogwatcher \
    && chmod 755 /usr/local/bin/blogwatcher \
    && rm -f /tmp/blogwatcher.tar.gz

RUN mkdir -p \
        /app/release-watch \
        /app/workspace \
        /app/output \
        /root/.agents/skills \
        /root/.codex/skills \
        /logs/agent/skills \
        /logs/verifier \
        /opt/task-baselines \
    && python3 /opt/productivity-tools-task-env/setup_environment.py \
    && chmod 755 /usr/local/bin/productivity-tools-entrypoint.sh \
    && chmod -R a+rwX /app /logs /root/.agents /root/.codex /opt/task-baselines

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/productivity-tools-entrypoint.sh"]
CMD ["/bin/bash"]
