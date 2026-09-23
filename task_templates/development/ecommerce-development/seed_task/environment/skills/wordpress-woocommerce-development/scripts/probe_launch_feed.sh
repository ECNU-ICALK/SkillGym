#!/bin/bash
set -euo pipefail

curl -fsS 'http://127.0.0.1/wp-json/harbor-printshop/v1/launch-feed'
echo
curl -fsS 'http://127.0.0.1/wp-json/harbor-printshop/v1/launch-feed?collection=portrait-studio'
echo
curl -fsS 'http://127.0.0.1/wp-json/harbor-printshop/v1/launch-feed?department=asian-art&in_stock_only=true'
echo
