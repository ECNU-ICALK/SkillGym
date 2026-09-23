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
        python3-psycopg2 \
        python3-pytest \
        nodejs \
        npm \
        postgresql \
        postgresql-client \
        postgresql-contrib \
        tini \
        ripgrep \
    && rm -rf /var/lib/apt/lists/*

COPY . /tmp/task-environment
COPY skills /tmp/task-environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /root/output /logs/agent /root/.codex \
    && cp -R /tmp/task-environment/data /root/data \
    && cp -R /tmp/task-environment/workspace /root/workspace \
    && chmod +x /root/workspace/bin/*.sh /root/workspace/run_rapid_transit_release.py \
    && chmod 755 /root \
    && chmod -R a+rX /root/data /root/workspace /root/output \
    && chmod -R a+rX /root/.codex /logs/agent

CMD ["/bin/bash"]
