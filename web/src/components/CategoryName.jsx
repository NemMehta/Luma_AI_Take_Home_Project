import { categoryLabel } from '../categories.js';

// A calm, readable category name tinted in its own category color (small
// same-color dot + friendly label). Replaces the raw-token chip in result cards.
export default function CategoryName({ category }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-medium" style={{ color: `var(--color-${category})` }}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {categoryLabel(category)}
    </span>
  );
}
