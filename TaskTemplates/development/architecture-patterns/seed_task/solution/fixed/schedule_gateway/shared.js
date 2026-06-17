const fs = require("fs");
const path = require("path");

class HttpError extends Error {
  constructor(statusCode, message) {
    super(message);
    this.statusCode = statusCode;
  }
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

function parsePositiveInt(value, fallback, maxValue) {
  if (value === undefined) {
    return fallback;
  }
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new HttpError(400, "limit must be a positive integer");
  }
  return Math.min(parsed, maxValue);
}

function requireDateParam(value) {
  const stringValue = String(value || "").trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(stringValue)) {
    throw new HttpError(400, "date must use YYYY-MM-DD");
  }
  return stringValue;
}

function requireTimeParam(value) {
  const stringValue = String(value || "").trim();
  if (!/^\d{2}:\d{2}:\d{2}$/.test(stringValue)) {
    throw new HttpError(400, "time must use HH:MM:SS");
  }
  return stringValue;
}

function providerSummary(provider) {
  return {
    id: provider.id,
    label: provider.label,
    kind: provider.kind,
    timezone: provider.timezone,
  };
}

function parseTimeToSeconds(value) {
  const [hours, minutes, seconds] = value.split(":").map((part) => Number.parseInt(part, 10));
  return (hours * 3600) + (minutes * 60) + seconds;
}

function secondsToTime(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const hh = String(hours).padStart(2, "0");
  const mm = String(minutes).padStart(2, "0");
  const ss = String(seconds).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function dataPath(dataRoot, relativePath) {
  return path.join(dataRoot, relativePath);
}

module.exports = {
  HttpError,
  dataPath,
  parsePositiveInt,
  parseTimeToSeconds,
  providerSummary,
  readJson,
  requireDateParam,
  requireTimeParam,
  secondsToTime,
};
