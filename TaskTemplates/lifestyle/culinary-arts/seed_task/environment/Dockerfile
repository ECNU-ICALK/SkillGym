FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV PAPRIKA_DATA_DIR=/opt/paprika_store
ENV PAPRIKA_ACCESS_LOG=/var/log/paprika_access.log

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        curl \
        findutils \
        gawk \
        grep \
        jq \
        nodejs \
        npm \
        sed \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir pytest pytest-json-report

COPY . /tmp/task-environment
COPY skills /tmp/task-environment/skills
COPY skills /logs/agent/skills

RUN mkdir -p /root/data /root/output /logs/agent/skills /logs/verifier /opt/paprika_store /opt/internal_tools \
    && cp -R /tmp/task-environment/data/. /root/data/ \
    && cp -R /tmp/task-environment/paprika_seed/. /opt/paprika_store/ \
    && cp /tmp/task-environment/paprika_cli/paprika.py /opt/internal_tools/mealops \
    && chmod 755 /opt/internal_tools/mealops \
    && if [ -f /logs/agent/skills/paprika/SKILL.md ]; then ln -sf /opt/internal_tools/mealops /usr/local/bin/paprika; fi \
    && cd /root/data \
    && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/paprika-input.sha256 \
    && cd /opt/paprika_store \
    && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/paprika-seed.sha256 \
    && sha256sum /opt/internal_tools/mealops > /opt/paprika-cli.sha256 \
    && chmod 644 /opt/paprika-input.sha256 /opt/paprika-seed.sha256 /opt/paprika-cli.sha256 \
    && touch /var/log/paprika_access.log \
    && chmod 666 /var/log/paprika_access.log \
    && chmod 777 /root/output

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
