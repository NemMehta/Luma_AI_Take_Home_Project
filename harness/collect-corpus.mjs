// Phase 4a: after running tests/corpus.spec.ts, copy each test's trace into
// ./corpus with a labeled name and write a manifest mapping each file to its
// true label and matching passing baseline. Runs regardless of the suite's exit
// code (the injected tests fail on purpose) and fails loudly if a trace is missing.

import { readdir, copyFile, mkdir, writeFile, stat } from 'node:fs/promises';
import { join } from 'node:path';

const TEST_RESULTS = 'test-results';
const CORPUS = 'corpus';

const CATEGORIES = {
  stale_selector: 'Test targets the old #search-box id; the box is now #search.',
  network_failure: 'Playwright route fails GET /api/fruits.json (HTTP 503) — data the app depends on.',
  real_bug: '?inject=real_bug inverts the filter, so search returns the non-matching fruits.',
  flaky_timing: '?inject=flaky paints the search result ~3s late; the test asserts within 1.5s.',
};

const norm = (s) => s.toLowerCase().replace(/[^a-z]/g, "");

async function findTraceZips(dir) {
  const out = [];
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...(await findTraceZips(path)));
    else if (entry.name === "trace.zip") out.push(path);
  }
  return out;
}

const zips = await findTraceZips(TEST_RESULTS);
if (zips.length === 0) {
  console.error(`No trace.zip under ${TEST_RESULTS}/. Did the corpus tests run with trace: 'on'?`);
  process.exit(1);
}

await mkdir(CORPUS, { recursive: true });

const traces = [];
const missing = [];

for (const [category, injection] of Object.entries(CATEGORIES)) {
  const catKey = norm(category);
  for (const variant of ["injected", "baseline"]) {
    const src = zips.find((z) => norm(z).includes(catKey) && norm(z).includes(variant));
    const dest = variant === "injected" ? `${category}.zip` : `${category}.baseline.zip`;
    if (!src) {
      missing.push(dest);
      continue;
    }
    const destPath = join(CORPUS, dest);
    await copyFile(src, destPath);
    const { size } = await stat(destPath);
    if (size < 1024) console.warn(`WARNING: ${destPath} is only ${size} bytes.`);
    console.log(`copied ${src} -> ${destPath} (${size} bytes)`);
    if (variant === "injected") {
      traces.push({ file: dest, label: category, outcome: "fail", baseline: `${category}.baseline.zip`, injection });
    } else {
      traces.push({ file: dest, label: "passing", outcome: "pass", baseline: null });
    }
  }
}

if (missing.length) {
  console.error(`Missing expected traces: ${missing.join(", ")}`);
  console.error(`trace.zips found:\n  ${zips.join("\n  ")}`);
  process.exit(1);
}

const manifest = {
  app: "harness/sut search flow",
  categories: Object.keys(CATEGORIES),
  traces,
};
await writeFile(join(CORPUS, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`\nWrote ${CORPUS}/manifest.json (${traces.length} traces).`);
