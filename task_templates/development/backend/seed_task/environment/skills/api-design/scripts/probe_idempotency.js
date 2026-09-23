const http = require("http");

function post(path, apiKey, idempotencyKey, payload) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        host: "127.0.0.1",
        port: Number(process.env.PORT || "8030"),
        path,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(JSON.stringify(payload)),
          "X-Partner-Key": apiKey,
          "Idempotency-Key": idempotencyKey
        }
      },
      (res) => {
        let body = "";
        res.on("data", (chunk) => {
          body += chunk;
        });
        res.on("end", () => {
          resolve({ status: res.statusCode, body: body ? JSON.parse(body) : null });
        });
      }
    );
    req.on("error", reject);
    req.write(JSON.stringify(payload));
    req.end();
  });
}

async function main() {
  const payload = {
    order_id: "ord_1004",
    amount: 10,
    reason: "customer_request"
  };

  const first = await post("/api/v1/refunds", "pk_live_gold_partner", "probe-idem-1", payload);
  const replay = await post("/api/v1/refunds", "pk_live_gold_partner", "probe-idem-1", payload);
  const conflicting = await post("/api/v1/refunds", "pk_live_gold_partner", "probe-idem-1", { ...payload, amount: 12 });

  console.log(JSON.stringify({ first, replay, conflicting }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
