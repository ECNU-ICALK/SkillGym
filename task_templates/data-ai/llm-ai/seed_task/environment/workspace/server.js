const app = require("./service/app");

const port = Number(process.env.PORT || "3000");

app.listen(port, "0.0.0.0", () => {
  process.stdout.write(`llm-ai-triage-template listening on ${port}\n`);
});
