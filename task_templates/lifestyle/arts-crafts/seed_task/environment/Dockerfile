FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV MODEL_SOURCE_PORT=443

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    curl \
    jq \
    npm \
    openssl \
    ripgrep \
    unzip \
    zip \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/arts-crafts-task-environment
COPY skills /opt/arts-crafts-task-environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /root/environment/data /root/.codex/skills /logs/agent/skills /root/answer /logs/verifier /services/model-source /srv/model-source/files /var/log/model-source \
    && cp -R /opt/arts-crafts-task-environment/data/. /root/environment/data/ \
    && cp -R /opt/arts-crafts-task-environment/services/model-source/. /services/model-source/ \
    && cp -R /opt/arts-crafts-task-environment/mirror/files/. /srv/model-source/files/ \
    && mkdir -p /services/model-source/tls \
    && openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
         -keyout /services/model-source/tls/model-source-ca.key \
         -out /services/model-source/tls/model-source-ca.crt \
         -subj '/CN=Model Source Local CA' \
    && printf '[req]\ndistinguished_name=req\nx509_extensions=v3_req\nprompt=no\n[dn]\nCN=api.printables.com\n[v3_req]\nsubjectAltName=@alt_names\nextendedKeyUsage=serverAuth\n[alt_names]\nDNS.1=api.printables.com\n' > /services/model-source/tls/server.cnf \
    && openssl req -new -newkey rsa:2048 -nodes \
         -keyout /services/model-source/tls/api.printables.com.key \
         -out /services/model-source/tls/api.printables.com.csr \
         -subj '/CN=api.printables.com' \
         -config /services/model-source/tls/server.cnf \
    && openssl x509 -req -sha256 -days 3650 \
         -in /services/model-source/tls/api.printables.com.csr \
         -CA /services/model-source/tls/model-source-ca.crt \
         -CAkey /services/model-source/tls/model-source-ca.key \
         -CAcreateserial \
         -out /services/model-source/tls/api.printables.com.crt \
         -extensions v3_req \
         -extfile /services/model-source/tls/server.cnf \
    && cp /services/model-source/tls/model-source-ca.crt /usr/local/share/ca-certificates/model-source-ca.crt \
    && update-ca-certificates \
    && printf '127.0.0.1 api.printables.com\n' >> /etc/hosts \
    && find /root/environment/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/model-bundle-data.sha256 \
    && find /services/model-source -type f -print0 | sort -z | xargs -0 sha256sum > /opt/model-source-service.sha256 \
    && find /srv/model-source/files -type f -print0 | sort -z | xargs -0 sha256sum > /opt/model-source-files.sha256 \
    && chmod -R 755 /services/model-source /srv/model-source \
    && chmod 644 /opt/model-bundle-data.sha256 /opt/model-source-service.sha256 /opt/model-source-files.sha256 \
    && chmod 777 /var/log/model-source

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"https://api.printables.com/healthz\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/model-source/server.py >/tmp/model-source.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"https://api.printables.com/healthz\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"https://api.printables.com/healthz\", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"model source service failed to start\" >&2\n\
  [ -f /tmp/model-source.log ] && cat /tmp/model-source.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-model-source \
    && chmod 755 /usr/local/bin/start-model-source

RUN printf '#!/bin/bash\n\
if command -v start-model-source >/dev/null 2>&1; then\n\
  start-model-source >/tmp/model-source-profile.log 2>&1 || true\n\
fi\n' > /etc/profile.d/model-source.sh \
    && chmod 644 /etc/profile.d/model-source.sh

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-model-source\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/arts-crafts-task-entrypoint \
    && chmod 755 /usr/local/bin/arts-crafts-task-entrypoint

ENTRYPOINT ["/usr/local/bin/arts-crafts-task-entrypoint"]
CMD ["/bin/bash"]
