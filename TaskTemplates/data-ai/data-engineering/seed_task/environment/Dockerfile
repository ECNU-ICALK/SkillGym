FROM ubuntu:24.04

USER root
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace
WORKDIR /app/workspace

# Copy skills to agent-specific locations
COPY skills /app/workspace/skills
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN chmod +x /app/workspace/run_pipeline.sh /app/workspace/pipeline/*.sh
