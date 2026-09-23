FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    curl \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir pandas==2.2.3 numpy==2.1.3 PyYAML==6.0.2

RUN mkdir -p /root/input /root/output /root/.codex/skills /logs/agent/skills /logs/verifier

COPY . /tmp/arkk-risk-environment

RUN cp -R /tmp/arkk-risk-environment/data/. /root/input/ \
    && if [ -d /tmp/arkk-risk-environment/skills ]; then cp -R /tmp/arkk-risk-environment/skills/. /root/.codex/skills/; fi \
    && if [ -d /tmp/arkk-risk-environment/skills ]; then cp -R /tmp/arkk-risk-environment/skills/. /logs/agent/skills/; fi \
    && rm -rf /tmp/arkk-risk-environment \
    && find /root/input -type f -print0 | sort -z | xargs -0 sha256sum > /opt/arkk-risk-input.sha256 \
    && chmod 644 /opt/arkk-risk-input.sha256 \
    && chmod -R a+r /root/input /root/.codex/skills /logs/agent/skills \
    && chmod 777 /root/output /logs/verifier

CMD ["/bin/bash"]
