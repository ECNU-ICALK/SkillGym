FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV WELLNESS_PLANNER_PORT=8147
ENV WELLNESS_PLANNER_SEED_DIR=/opt/wellness-planner/seed

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    tini \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /services/wellness-planner \
    /opt/wellness-planner/seed \
    /root/data \
    /root/output \
    /root/.codex/skills \
    /logs/agent/skills \
    /logs/verifier \
    /var/log/wellness-planner

COPY data /root/data
COPY service_seed /opt/wellness-planner/seed
COPY hidden-service-src/server.py /services/wellness-planner/server.py
COPY scripts/start-wellness-planner.sh /usr/local/bin/start-wellness-planner
COPY scripts/wellness-entrypoint.sh /usr/local/bin/wellness-entrypoint
COPY scripts/wellness-start-planner-profile.sh /etc/profile.d/wellness-start-planner.sh
COPY . /tmp/environment
COPY skills /tmp/environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN python3 /tmp/environment/build_runtime_service.py \
    && rm -rf /tmp/environment \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/wellness-data.sha256 \
    && chmod 755 /services/wellness-planner/server.py \
    && chmod 755 /opt/wellness-runtime/server_runtime.pyc \
    && chmod 755 /usr/local/bin/start-wellness-planner /usr/local/bin/wellness-entrypoint /etc/profile.d/wellness-start-planner.sh \
    && chmod -R a+rX /root/data /opt/wellness-planner/seed /root/.codex/skills /logs/agent/skills /opt/wellness-runtime \
    && chmod 777 /root/output /var/log/wellness-planner

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/wellness-entrypoint"]
CMD ["/bin/bash"]
