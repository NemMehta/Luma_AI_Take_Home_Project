// Human-readable names + one-line explanations for the diagnosis categories, so
// the UI reads in plain English instead of repeating the raw category token.
// Single source of truth shared by the upload card and the known-bugs rows.
export const CATEGORY_META = {
  real_bug:        { label: 'Real bug',        blurb: 'A genuine defect in the app itself, not a flaw in the test.' },
  stale_selector:  { label: 'Stale selector',  blurb: 'The test looked for an element the app no longer has.' },
  flaky_timing:    { label: 'Flaky timing',    blurb: 'The app was just slow; the test gave up before it finished.' },
  network_failure: { label: 'Network failure', blurb: 'A request the app relies on failed or never came back.' },
  race_condition:  { label: 'Race condition',  blurb: 'Two steps ran out of order, so the test saw an in-between state.' },
};

export const categoryLabel = (c) => CATEGORY_META[c]?.label ?? c;
export const categoryBlurb = (c) => CATEGORY_META[c]?.blurb ?? '';
