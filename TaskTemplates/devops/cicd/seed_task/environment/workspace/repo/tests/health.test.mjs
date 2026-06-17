import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("server exposes the documented health path", async () => {
  const source = await readFile(new URL("../app/server.mjs", import.meta.url), "utf8");
  assert.match(source, /\/healthz/);
  assert.match(source, /saturn-checkout/);
});
