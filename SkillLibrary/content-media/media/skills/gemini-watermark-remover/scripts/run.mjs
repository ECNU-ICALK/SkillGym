import { spawn, spawnSync } from 'node:child_process';
import { access } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const localBinPath = fileURLToPath(new URL('../../../bin/gwr.mjs', import.meta.url));
const WINDOWS_SHELL = process.env.ComSpec || 'cmd.exe';
const DEFAULT_CLI_PACKAGE_SPEC = process.env.GWR_SKILL_CLI_SPEC || '@pilio/gemini-watermark-remover';

function quoteWindowsCommandArg(value) {
  const stringValue = String(value);
  if (stringValue.length === 0) return '""';

  if (!/[\s"]/u.test(stringValue)) {
    return stringValue;
  }

  return `"${stringValue.replace(/(\\*)"/g, '$1$1\\"').replace(/(\\+)$/g, '$1$1')}"`;
}

function buildWindowsCommandLine(command, args) {
  return [command, ...args].map(quoteWindowsCommandArg).join(' ');
}

function buildWindowsShellCandidate(command, args) {
  return {
    command: WINDOWS_SHELL,
    commandArgs: ['/d', '/s', '/c', buildWindowsCommandLine(command, args)]
  };
}

function hasPathCommand(command) {
  const lookup = process.platform === 'win32'
    ? spawnSync('where.exe', [command], { stdio: 'ignore' })
    : spawnSync('which', [command], { stdio: 'ignore' });

  return lookup.status === 0;
}

function getPathFallbackCandidates(args) {
  if (process.platform === 'win32') {
    const candidates = [];
    if (hasPathCommand('gwr')) {
      candidates.push(buildWindowsShellCandidate('gwr', args));
    }
    if (hasPathCommand('pnpm')) {
      candidates.push(buildWindowsShellCandidate('pnpm', ['dlx', DEFAULT_CLI_PACKAGE_SPEC, ...args]));
    }
    return candidates;
  }

  const candidates = [];
  if (hasPathCommand('gwr')) {
    candidates.push({ command: 'gwr', commandArgs: args });
  }
  if (hasPathCommand('pnpm')) {
    candidates.push({ command: 'pnpm', commandArgs: ['dlx', DEFAULT_CLI_PACKAGE_SPEC, ...args] });
  }
  return candidates;
}

async function resolveCliCandidates(args) {
  try {
    await access(localBinPath);
    return [{
      command: process.execPath,
      commandArgs: [localBinPath, ...args]
    }];
  } catch {
    return getPathFallbackCandidates(args);
  }
}

function spawnOnce(command, commandArgs, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, {
      stdio: ['ignore', 'pipe', 'pipe'],
      ...options
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });
    child.on('error', reject);
    child.on('close', (code) => resolve({ code, stdout, stderr }));
  });
}

export async function runSkillCli(args, options = {}) {
  const candidates = await resolveCliCandidates(args);
  let lastSpawnError = null;

  for (const { command, commandArgs } of candidates) {
    try {
      return await spawnOnce(command, commandArgs, options);
    } catch (error) {
      if (error && (error.code === 'ENOENT' || error.code === 'EINVAL')) {
        lastSpawnError = error;
        continue;
      }

      throw error;
    }
  }

  if (lastSpawnError) {
    throw lastSpawnError;
  }

  throw new Error('Unable to locate gwr CLI executable');
}

function isDirectRun() {
  if (!process.argv[1]) {
    return false;
  }

  return resolve(process.argv[1]) === fileURLToPath(import.meta.url);
}

export async function main(argv = process.argv.slice(2)) {
  const { code, stdout, stderr } = await runSkillCli(argv);

  if (stdout) {
    process.stdout.write(stdout);
  }
  if (stderr) {
    process.stderr.write(stderr);
  }

  if (typeof code !== 'number') {
    return 1;
  }

  return code;
}

if (isDirectRun()) {
  main()
    .then((exitCode) => {
      process.exitCode = exitCode;
    })
    .catch((error) => {
      const message = error instanceof Error ? error.message : String(error);
      process.stderr.write(`${message}\n`);
      process.exitCode = 1;
    });
}
