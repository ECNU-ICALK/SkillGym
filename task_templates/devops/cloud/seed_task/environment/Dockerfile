FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        gnupg \
        jq \
        unzip \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSLo /tmp/terraform.zip https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && rm -f /tmp/terraform.zip

RUN pip install --no-cache-dir pytest python-hcl2

COPY . /root/environment
COPY skills /root/environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /root/.codex/skills /logs/agent/skills /logs/verifier \
    && if [ -f /root/environment/skills/22__terraform-module-library/references/harbor-vpc-module-checklist.md ]; then cp /root/environment/skills/22__terraform-module-library/references/harbor-vpc-module-checklist.md /root/environment/workspace/terraform-modules/aws/vpc/SKILL_HINT.md; fi

WORKDIR /root/environment
