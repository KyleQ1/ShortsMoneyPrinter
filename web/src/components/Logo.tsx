export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span
      className={
        compact
          ? "relative inline-flex h-7 w-10 shrink-0 items-center justify-center rounded-md bg-accent text-white shadow-inner"
          : "relative inline-flex h-8 w-12 shrink-0 items-center justify-center rounded-md bg-accent text-white shadow-inner"
      }
      aria-hidden="true"
    >
      <span className="absolute h-6 w-1 rounded-full bg-white" />
      <span className="relative text-2xl font-black leading-none">S</span>
    </span>
  );
}
