const { createApp } = require("./service/app");

const port = Number(process.env.PORT || "8030");
const app = createApp();

app.listen(port, () => {
  process.stdout.write(`partner-order-refund-api listening on ${port}\n`);
});
