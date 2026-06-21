// Full class strings (not built dynamically) so Tailwind keeps them in the build.
const STYLES = {
  real_bug: 'bg-rose-100 text-rose-700 ring-rose-600/20',
  stale_selector: 'bg-amber-100 text-amber-800 ring-amber-600/20',
  flaky_timing: 'bg-violet-100 text-violet-700 ring-violet-600/20',
  network_failure: 'bg-sky-100 text-sky-700 ring-sky-600/20',
  race_condition: 'bg-pink-100 text-pink-700 ring-pink-600/20',
};

export default function CategoryBadge({ category }) {
  const style = STYLES[category] ?? 'bg-slate-100 text-slate-700 ring-slate-600/20';
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-xs font-medium ring-1 ring-inset ${style}`}>
      {category ?? 'unknown'}
    </span>
  );
}
