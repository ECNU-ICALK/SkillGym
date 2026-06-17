const http = require("http");

function request(path, apiKey) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        host: "127.0.0.1",
        port: Number(process.env.PORT || "8030"),
        path,
        method: "GET",
        headers: apiKey ? { "X-Partner-Key": apiKey } : {}
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
    req.end();
  });
}

async function main() {
  const authMissing = await request("/api/v1/orders?page=1&page_size=2");
  const page1 = await request("/api/v1/orders?page=1&page_size=2&status=paid&sort=-created_at", "pk_live_gold_partner");
  const page1Again = await request("/api/v1/orders?page=1&page_size=2&status=paid&sort=-created_at", "pk_live_gold_partner");
  console.log(JSON.stringify({ authMissing, page1, page1Again }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
