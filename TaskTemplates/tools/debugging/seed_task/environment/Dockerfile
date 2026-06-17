FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    nodejs \
    npm \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

COPY . /tmp/environment/
COPY skills /logs/agent/skills
COPY skills /app/skills
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN mkdir -p /root/data /root/artifacts /root/output /root/app /app /app/skills \
    /root/.claude/skills /root/.codex/skills /root/.opencode/skill /root/.goose/skills \
    /root/.factory/skills /root/.agents/skills /root/.gemini/skills /logs/agent/skills /logs/verifier \
    && cp -R /tmp/environment/data/. /root/data/ \
    && cp -R /tmp/environment/artifacts/. /root/artifacts/ \
    && cp -R /tmp/environment/app/. /root/app/ \
    && cp -R /tmp/environment/app/. /app/ \
    && chmod 755 /root \
    && chmod -R a+rX /root/data /root/artifacts /root/app /app /root/.codex/skills /logs/agent/skills \
    && chmod 777 /root/output \
    && rm -rf /tmp/environment

WORKDIR /app

ENTRYPOINT ["/bin/bash", "-lc"]
CMD ["exec /bin/bash"]
