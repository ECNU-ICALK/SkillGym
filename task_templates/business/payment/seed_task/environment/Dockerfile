FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV AP_REVIEW_PORT=8148

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pyyaml pypdf

COPY . /opt/payment-env

RUN mkdir -p /services/ap-review /root/.codex/skills /logs/agent/skills /root/output /logs/verifier /var/log/ap-review \
    && cp -R /opt/payment-env/data /root/data \
    && cp -R /opt/payment-env/hidden-service-src/. /services/ap-review/ \
    && if [ -d /opt/payment-env/skills ]; then cp -R /opt/payment-env/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/payment-env/skills ]; then cp -R /opt/payment-env/skills/. /logs/agent/skills/; fi \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/payment-data.sha256 \
    && find /services/ap-review -type f -print0 | sort -z | xargs -0 sha256sum > /opt/payment-service.sha256 \
    && if [ -d /root/.codex/skills ] && find /root/.codex/skills -type f | grep -q .; then find /root/.codex/skills -type f -print0 | sort -z | xargs -0 sha256sum > /opt/payment-skills.sha256; fi \
    && chmod -R 755 /services/ap-review \
    && chmod 644 /opt/payment-data.sha256 /opt/payment-service.sha256 \
    && if [ -f /opt/payment-skills.sha256 ]; then chmod 644 /opt/payment-skills.sha256; fi \
    && chmod 777 /var/log/ap-review

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8148/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/ap-review/server.py >/tmp/ap-review.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8148/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8148/health", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"ap review service failed to start\" >&2\n\
  [ -f /tmp/ap-review.log ] && cat /tmp/ap-review.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-ap-review \
    && chmod 755 /usr/local/bin/start-ap-review

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-ap-review\n\
if [ "$#" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ "$#" -eq 1 ]; then\n\
  exec /bin/bash -lc "$1"\n\
else\n\
  exec "$@"\n\
fi\n' > /usr/local/bin/payment-entrypoint \
    && chmod 755 /usr/local/bin/payment-entrypoint

RUN printf '#!/bin/bash\n\
/usr/local/bin/start-ap-review >/dev/null 2>&1 || true\n' > /etc/profile.d/payment-start-ap-review.sh \
    && chmod 755 /etc/profile.d/payment-start-ap-review.sh

ENTRYPOINT ["/usr/local/bin/payment-entrypoint"]
CMD ["/bin/bash"]
