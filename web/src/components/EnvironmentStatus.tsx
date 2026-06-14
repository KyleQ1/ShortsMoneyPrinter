import type { PreflightStatus } from "../types";

export function EnvironmentStatus({ status }: { status: PreflightStatus | null }) {
  const checks: Array<[string, boolean, string]> = status
    ? [
        ["ffmpeg", status.ffmpeg, "Video encoding"],
        ["ffprobe", status.ffprobe, "Media inspection"],
        ["yt-dlp", status.yt_dlp, "URL download"],
        ["Seedance2 cookie", status.seedance2_cookie, "Temporary direct Seedance test run"],
        ["Replicate token", status.replicate_token, "Cloud generation auth"],
        ["Replicate package", status.replicate_package, "Cloud generation SDK"],
      ]
    : [];

  const ready = checks.filter(([, ok]) => ok).length;
  const total = checks.length;

  return (
    <section className="panel animate-fade-up">
      <div className="flex items-center justify-between">
        <h2 className="section-title">Environment</h2>
        {status ? (
          <span className="text-xs font-semibold text-muted">
            <span className={ready === total ? "text-success" : "text-warning"}>{ready}</span>/{total} ready
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid gap-1.5">
        {status ? (
          checks.map(([label, ok, hint]) => (
            <div
              key={label}
              className="flex items-center gap-2.5 rounded-lg border border-line/70 bg-surface-2/40 px-3 py-2"
              title={hint}
            >
              <span
                className={
                  ok
                    ? "grid h-4 w-4 place-items-center rounded-full bg-success/15 text-success"
                    : "grid h-4 w-4 place-items-center rounded-full bg-warning/15 text-warning"
                }
              >
                {ok ? (
                  <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
                ) : (
                  <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"><path d="M12 8v5M12 16.5v.01" /></svg>
                )}
              </span>
              <span className="flex-1 text-sm text-ink">{label}</span>
              <span className="text-xs text-faint">{hint}</span>
            </div>
          ))
        ) : (
          <div className="flex items-center gap-2 rounded-lg border border-line/70 bg-surface-2/40 px-3 py-2 text-sm text-muted">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line border-t-accent" />
            Checking environment…
          </div>
        )}
      </div>
    </section>
  );
}
