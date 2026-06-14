export function Logo({ compact = false }: { compact?: boolean }) {
  const size = compact ? "h-9 w-9" : "h-10 w-10";
  return (
    <span
      className={`relative inline-grid ${size} shrink-0 place-items-center overflow-hidden rounded-xl bg-accent-gradient shadow-glow-soft`}
      aria-hidden="true"
    >
      {/* play triangle */}
      <svg viewBox="0 0 24 24" className="relative h-5 w-5 text-night" fill="currentColor">
        <path d="M8 5.5v13a1 1 0 0 0 1.54.84l10-6.5a1 1 0 0 0 0-1.68l-10-6.5A1 1 0 0 0 8 5.5Z" />
      </svg>
      {/* subtle sheen */}
      <span className="pointer-events-none absolute -left-2 top-0 h-full w-1/2 -skew-x-12 bg-white/25 blur-md" />
    </span>
  );
}
