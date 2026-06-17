FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.codex/skills/domain-name-brainstormer/bin:${PATH}" \
    BASH_ENV=/etc/codex-command-hint.sh

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    nodejs \
    npm \
    python3 \
    python3-pandas \
    python3-pytest \
    python-is-python3 \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/workspace/data /root/output /root/.codex/skills

COPY data /root/workspace/data
COPY skills /root/workspace/skills
COPY skills /root/.codex/skills

RUN if [ -f /root/.codex/skills/domain-name-brainstormer/references/installed_procedure.md ]; then \
      cp /root/.codex/skills/domain-name-brainstormer/references/installed_procedure.md /root/workspace/installed_procedure.md; \
    fi

RUN if [ -x /root/.codex/skills/domain-name-brainstormer/bin/domain-snapshot-audit ]; then \
      ln -sf /root/.codex/skills/domain-name-brainstormer/bin/domain-snapshot-audit /usr/local/bin/domain-snapshot-audit; \
    fi \
    && if [ -x /root/.codex/skills/domain-name-brainstormer/bin/domain-shortlist-procedure ]; then \
      ln -sf /root/.codex/skills/domain-name-brainstormer/bin/domain-shortlist-procedure /usr/local/bin/domain-shortlist-procedure; \
    fi

RUN printf '%s\n' \
  'if [ -x /root/.codex/skills/domain-name-brainstormer/bin/domain-snapshot-audit ]; then' \
  '  export DOMAIN_NAME_BRAINSTORMER_HOME=/root/.codex/skills/domain-name-brainstormer' \
  '  export DOMAIN_NAME_BRAINSTORMER_AUDIT_CMD="domain-snapshot-audit --data-dir /root/workspace/data --output-dir /root/output"' \
  '  echo "[domain-name-brainstormer] installed procedure found: use domain-snapshot-audit --data-dir /root/workspace/data --output-dir /root/output before deriving manual scores." >&2' \
  '  echo "[domain-name-brainstormer] policy reference: /root/.codex/skills/domain-name-brainstormer/references/domain_selection_policy.json" >&2' \
  'fi' > /etc/codex-command-hint.sh \
  && cp /etc/codex-command-hint.sh /etc/profile.d/domain-name-brainstormer.sh

RUN find /root/workspace/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/domain-source-bundle.sha256
