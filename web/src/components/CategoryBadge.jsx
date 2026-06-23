// Full class strings (not built dynamically) so Tailwind keeps them in the build.
// Colors come from the category tokens in index.css — no hex here.
const STYLES = {
  real_bug: 'bg-real_bug/10 text-real_bug ring-real_bug/30',
  stale_selector: 'bg-stale_selector/10 text-stale_selector ring-stale_selector/30',
  flaky_timing: 'bg-flaky_timing/10 text-flaky_timing ring-flaky_timing/30',
  network_failure: 'bg-network_failure/10 text-network_failure ring-network_failure/30',
  race_condition: 'bg-race_condition/10 text-race_condition ring-race_condition/30',
};

export default function CategoryBadge({ category }) {
  const style = STYLES[category] ?? 'bg-ink/5 text-muted ring-hair';
  // Each badge is a Darkroom-style "chip": lit from within in its own category
  // color via the --glow variable that .glow/.glow-pulse read.
  return (
    <span
      style={{ '--glow': category ? `var(--color-${category})` : 'transparent' }}
      className={`glow glow-pulse inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-xs font-medium ring-1 ring-inset ${style}`}
    >
      {category ?? 'unknown'}
    </span>
  );
}
