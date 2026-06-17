const fs = require('fs');
const path = require('path');

const workspaceRoot = process.cwd();
const dataDir = process.env.DATA_DIR ? path.resolve(process.env.DATA_DIR) : path.join(workspaceRoot, 'data');
const stateDir = process.env.STATE_DIR ? path.resolve(process.env.STATE_DIR) : path.join(workspaceRoot, 'state');
const outputDir = process.env.OUTPUT_DIR ? path.resolve(process.env.OUTPUT_DIR) : path.join(workspaceRoot, 'output', 'exports');

fs.mkdirSync(stateDir, { recursive: true });
fs.mkdirSync(outputDir, { recursive: true });

const seed = JSON.parse(fs.readFileSync(path.join(dataDir, 'export_jobs.json'), 'utf8'));
const jobs = Array.isArray(seed.jobs) ? seed.jobs : [];
const runtimeState = {
  request_counters: {},
  export_jobs: jobs,
  next_export_job_seq: jobs.length + 1,
};

fs.writeFileSync(path.join(stateDir, 'runtime_state.json'), JSON.stringify(runtimeState, null, 2) + '\n', 'utf8');

for (const entry of fs.readdirSync(outputDir)) {
  if (entry.endsWith('.csv')) {
    fs.unlinkSync(path.join(outputDir, entry));
  }
}
