const { buildBriefings } = require("./core");

const outputFiles = buildBriefings();
for (const filePath of outputFiles) {
  console.log(filePath);
}
