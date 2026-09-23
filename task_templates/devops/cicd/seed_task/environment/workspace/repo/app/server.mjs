import http from "node:http";

const port = Number(process.env.PORT || 8080);

const server = http.createServer((request, response) => {
  if (request.url === "/healthz") {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ service: "saturn-checkout", status: "ok" }));
    return;
  }

  response.writeHead(200, { "content-type": "application/json" });
  response.end(JSON.stringify({ service: "saturn-checkout", message: "checkout ready" }));
});

server.listen(port, "0.0.0.0", () => {
  process.stdout.write(`saturn-checkout listening on ${port}\n`);
});
