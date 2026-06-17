const path = require("path");
const { createApp } = require("./schedule_gateway/app");

const dataRoot = process.env.SCHEDULE_DATA_ROOT || path.join(__dirname, "data");
const port = Number(process.env.PORT || 3000);

const app = createApp({ dataRoot });

app.listen(port, () => {
  process.stdout.write(`schedule-gateway listening on ${port}\n`);
});
