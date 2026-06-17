FROM node:22-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV NEXT_TELEMETRY_DISABLED=1
ENV PAYLOAD_SECRET=met-highlight-secret
ENV DATABASE_URL=file:./runtime/payload.db
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app/workspace

COPY workspace/package.json /app/workspace/package.json
COPY workspace/tsconfig.json /app/workspace/tsconfig.json
COPY workspace/next-env.d.ts /app/workspace/next-env.d.ts
COPY workspace/next.config.ts /app/workspace/next.config.ts

RUN npm install --legacy-peer-deps

COPY workspace /app/workspace
COPY data /app/data
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN chmod +x /app/workspace/scripts/run_smoke_checks.sh
