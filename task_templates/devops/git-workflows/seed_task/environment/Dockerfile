FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV TASK_ROOT=/app
ENV TASK_REPO_ROOT=/app/repo
ENV TASK_DATA_ROOT=/root/data
ENV TASK_OUTPUT_ROOT=/root/output

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl git jq nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest

COPY . /opt/meridian-task-env
COPY skills /opt/meridian-task-env/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /root/.codex/skills /logs/agent/skills /logs/verifier /root/output /opt/task-baselines \
    && cp -R /opt/meridian-task-env/data /root/data \
    && python3 /opt/meridian-task-env/bootstrap/create_meridian_repo.py \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/data.sha256 \
    && chmod -R 755 /opt/meridian-task-env/bootstrap \
    && chmod 644 /opt/task-baselines/data.sha256

ENTRYPOINT ["/bin/bash", "-lc"]
CMD ["exec /bin/bash"]
