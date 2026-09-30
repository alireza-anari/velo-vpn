export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className={compact ? "brand-mark brand-mark--compact" : "brand-mark"} aria-hidden="true">
      <svg viewBox="0 0 80 80" role="img">
        <path d="M15 19c10 2 18 8 25 18 7-10 15-16 25-18-5 19-13 32-25 43C28 51 20 38 15 19Z" />
        <path className="brand-mark-inner" d="M25 25c6 4 11 9 15 15 4-6 9-11 15-15-4 10-9 19-15 26-6-7-11-16-15-26Z" />
      </svg>
    </div>
  );
}
