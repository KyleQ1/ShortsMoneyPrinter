import { Logo } from "./Logo";

export function Header() {
  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <Logo />
          <div>
            <h1 className="text-base font-extrabold leading-tight text-ink">ShortsMoneyPrinter</h1>
            <p className="text-xs text-muted">Local Wan remix planner with optional cloud models</p>
          </div>
        </div>
        <span className="pill">Local first</span>
      </div>
    </header>
  );
}
