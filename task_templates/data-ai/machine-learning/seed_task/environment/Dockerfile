FROM python:3.11-slim

WORKDIR /root

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tini \
        curl \
        ca-certificates \
        unzip \
        ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        numpy \
        pandas \
        scikit-learn \
        pytest

RUN mkdir -p /tmp/wheels \
    && curl -L --retry 8 --retry-delay 5 --max-time 1200 \
        "https://download.pytorch.org/whl/cpu/torch-2.5.1%2Bcpu-cp311-cp311-linux_x86_64.whl" \
        -o /tmp/wheels/torch-2.5.1+cpu-cp311-cp311-linux_x86_64.whl \
    && python -m pip install --no-cache-dir /tmp/wheels/torch-2.5.1+cpu-cp311-cp311-linux_x86_64.whl \
    && rm -rf /tmp/wheels

COPY . /root/environment
COPY skills /root/environment/skills
COPY skills /root/.codex/skills

RUN python /root/environment/generate_seed_data.py \
    && mkdir -p /root/.codex \
    && chmod +x /root/environment/project/run_pipeline.py \
    && mkdir -p /root/answer
