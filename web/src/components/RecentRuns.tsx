import { useState } from "react";
import { classNames, formatSeconds, money, shortText } from "../lib";
import type { RunPlan } from "../types";
import { StatusPill, statusTone } from "./StatusPill";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "planned", label: "Planned" },
  { key: "done", label: "Done" },
] as const;

type Filter = (typeof FILTERS)[number]["key"];

export function RecentRuns({
  runs,
  onRefresh,
  onSelect,
}: {
  runs: RunPlan[];
  onRefresh: () => void;
  onSelect: (runId: string) => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const filtered = runs.filter((run) => (filter === "all" ? true : run.status === filter));

  return (
    <section className="panel animate-fade-up">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-extrabold tracking-tight text-ink">Recent Runs</h2>
        <button className="btn-secondary min-h-9 px-3 py-1.5 text-xs" type="button" onClick={onRefresh}>
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5" /></svg>
          Refresh
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {FILTERS.map(({ key, label }) => {
          const count = key === "all" ? runs.length : runs.filter((run) => run.status === key).length;
          return (
            <button
              key={key}
              type="button"
              className={classNames(
                "rounded-full border px-3 py-1 text-xs font-semibold transition",
                filter === key
                  ? "border-transparent bg-accent-gradient text-night"
                  : "border-line bg-surface-2/60 text-muted hover:border-accent/50 hover:text-accent",
              )}
              onClick={() => setFilter(key)}
            >
              {label} ({count})
            </button>
          );
        })}
      </div>

      <div className="mt-4 grid gap-3">
        {filtered.length ? (
          filtered.slice(0, 8).map((run) => {
            const isDone = run.status === "done" && Boolean(run.final_path);
            const sourceSrc = `/api/runs/${run.run_id}/source.mp4`;
            const finalSrc = `/api/runs/${run.run_id}/final.mp4`;
            return (
              <div className="rounded-xl border border-line bg-surface-2/40 p-3.5 transition hover:border-line-strong" key={run.run_id}>
                <button className="grid w-full gap-1 text-left transition hover:opacity-90" type="button" onClick={() => onSelect(run.run_id)}>
                  <span className="flex flex-wrap items-center gap-2">
                    <b className="font-mono text-sm text-ink">{run.run_id}</b>
                    <StatusPill tone={statusTone(run.status)}>{run.status}</StatusPill>
                    <StatusPill>{run.quality}</StatusPill>
                  </span>
                  <span className="truncate text-xs text-muted">
                    {shortText(run.source_title || run.source, "source", 80)} · {formatSeconds(run.duration)} · {money(run.estimated_cost)}
                  </span>
                </button>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <Clip label="Original" src={sourceSrc} />
                  {isDone ? <Clip label="Generated" src={finalSrc} download accent /> : null}
                </div>
              </div>
            );
          })
        ) : (
          <p className="hint">No {filter === "all" ? "" : `${filter} `}runs yet.</p>
        )}
      </div>
    </section>
  );
}

function Clip({ label, src, download, accent }: { label: string; src: string; download?: boolean; accent?: boolean }) {
  return (
    <div>
      <span className={classNames("mb-1.5 block text-[11px] font-bold uppercase tracking-wider", accent ? "text-accent" : "text-faint")}>{label}</span>
      <video className="aspect-[9/16] w-full max-w-[170px] rounded-lg border border-line bg-black object-contain" controls preload="metadata" src={src} />
      {download ? (
        <a className="mt-1.5 inline-flex items-center gap-1 text-xs font-bold text-accent hover:underline" href={src} download>
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v12m0 0 4-4m-4 4-4-4M4 21h16" /></svg>
          Download MP4
        </a>
      ) : null}
    </div>
  );
}
