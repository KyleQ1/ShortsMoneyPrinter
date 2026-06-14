import { Logo } from "./Logo";

const REPO_URL = "https://github.com/";

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-night/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <Logo />
          <div className="leading-tight">
            <h1 className="text-[15px] font-extrabold tracking-tight text-ink">
              Shorts<span className="text-gradient">MoneyPrinter</span>
            </h1>
            <p className="text-xs text-muted">AI Video Remix Studio</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="hidden items-center gap-1.5 rounded-full border border-accent/30 bg-accent-soft/40 px-3 py-1 text-xs font-semibold text-accent sm:inline-flex">
            <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-[0_0_8px_rgba(45,212,191,0.9)]" />
            Local first
          </span>
          <a
            className="inline-flex items-center gap-2 rounded-full border border-line-strong bg-surface-2/70 px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-accent/50 hover:text-accent"
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            title="Star on GitHub"
          >
            <svg viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor" aria-hidden="true">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
            </svg>
            <span className="hidden sm:inline">Star</span>
          </a>
        </div>
      </div>
    </header>
  );
}
