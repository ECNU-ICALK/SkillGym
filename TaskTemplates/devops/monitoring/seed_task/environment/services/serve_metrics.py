#!/usr/bin/env python3
import argparse
import json
import math
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

BUCKETS = [0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 2.0, math.inf]


def render_metrics(profile: dict, service: str, started_at: float) -> str:
    elapsed = max(time.time() - started_at, 1.0)
    total_requests = profile["request_rate_rps"] * elapsed
    error_count = total_requests * (profile["error_rate_pct"] / 100.0)
    ok_count = total_requests - error_count
    count = total_requests
    fractions = profile["latency_fractions"]
    duration_sum = total_requests * profile["request_rate_rps"] * 0.01
    lines = [
        "# HELP harbor_http_requests_total Total HTTP requests served.",
        "# TYPE harbor_http_requests_total counter",
        f'harbor_http_requests_total{{code="200",method="GET"}} {ok_count:.6f}',
        f'harbor_http_requests_total{{code="500",method="GET"}} {error_count:.6f}',
        "# HELP harbor_http_request_duration_seconds Request latency histogram.",
        "# TYPE harbor_http_request_duration_seconds histogram"
    ]
    for boundary, fraction in zip(BUCKETS, fractions):
        value = count * fraction
        le = "+Inf" if math.isinf(boundary) else f"{boundary:g}"
        lines.append(
            f'harbor_http_request_duration_seconds_bucket{{method="GET",le="{le}"}} {value:.6f}'
        )
    lines.extend(
        [
            f"harbor_http_request_duration_seconds_sum{{method=\"GET\"}} {duration_sum:.6f}",
            f"harbor_http_request_duration_seconds_count{{method=\"GET\"}} {count:.6f}",
            "# HELP harbor_build_info Build marker.",
            "# TYPE harbor_build_info gauge",
            f'harbor_build_info{{service_name="{service}"}} 1'
        ]
    )
    return "\n".join(lines) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    profile = None
    service = ""
    started_at = 0.0
    metrics_path = "/metrics"

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok\n")
            return
        if self.path != self.metrics_path:
            self.send_response(404)
            self.end_headers()
            return
        body = render_metrics(self.profile, self.service, self.started_at).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--service", required=True)
    args = parser.parse_args()
    with open(args.profiles, "r", encoding="utf-8") as handle:
        profiles = json.load(handle)
    profile = profiles[args.service]
    handler = type("BoundHandler", (MetricsHandler,), {})
    handler.profile = profile
    handler.service = args.service
    handler.started_at = time.time()
    handler.metrics_path = profile.get("metrics_path", "/metrics")
    server = HTTPServer(("127.0.0.1", int(profile["port"])), handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
