// After a test run, copy the two Playwright traces into ./samples with stable
// names so later phases (parser/classifier) have fixed raw material to read.
// Runs regardless of the run's exit code (the stale-selector test fails on
// purpose), and fails loudly if either expected trace is missing.

import { readdir, copyFile, mkdir, stat } from 'node:fs/promises';
import { join } from 'node:path';

const TEST_RESULTS = 'test-results';
const SAMPLES = 'samples';

// Match a token in Playwright's per-test output-dir name -> destination name.
const TARGETS = [
  { match: /stale-selector|failing/i, dest: 'failing_stale_selector.zip' },
  { match: /happy|passing/i, dest: 'passing.zip' },
];

async function findTraceZips(dir) {
  const found = [];
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return found;
  }
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) found.push(...(await findTraceZips(path)));
    else if (entry.name === 'trace.zip') found.push(path);
  }
  return found;
}

const zips = await findTraceZips(TEST_RESULTS);
if (zips.length === 0) {
  console.error(`No trace.zip found under ${TEST_RESULTS}/. Did the tests run with trace: 'on'?`);
  process.exit(1);
}

await mkdir(SAMPLES, { recursive: true });

const missing = [];
for (const { match, dest } of TARGETS) {
  const src = zips.find((zip) => match.test(zip));
  if (!src) {
    missing.push(dest);
    continue;
  }
  const destPath = join(SAMPLES, dest);
  await copyFile(src, destPath);
  const { size } = await stat(destPath);
  console.log(`copied ${src} -> ${destPath} (${size} bytes)`);
  if (size < 1024) console.warn(`WARNING: ${destPath} is only ${size} bytes — it may be empty.`);
}

if (missing.length > 0) {
  console.error(`Missing trace(s): ${missing.join(', ')}`);
  console.error(`trace.zip files found:\n  ${zips.join('\n  ')}`);
  process.exit(1);
}

console.log('Samples updated.');
