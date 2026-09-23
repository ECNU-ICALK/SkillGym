const { createApp } = require('./service/app');

const port = Number(process.env.PORT || 3000);
const app = createApp({
  dataDir: process.env.DATA_DIR,
  stateDir: process.env.STATE_DIR,
  outputDir: process.env.OUTPUT_DIR,
});

app.listen(port, '127.0.0.1', () => {
  process.stdout.write(`listening on ${port}\n`);
});
