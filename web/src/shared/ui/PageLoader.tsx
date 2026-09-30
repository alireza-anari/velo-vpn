export function PageLoader({ label }: { label: string }) {
  return (
    <main className="loader-shell" aria-live="polite">
      <span className="loader" aria-hidden="true" />
      <span>{label}</span>
    </main>
  );
}
