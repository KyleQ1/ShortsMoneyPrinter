import { formatSeconds, money, shortText } from "../lib";
import type { RunPlan } from "../types";
import { StatusPill, statusTone } from "./StatusPill";

export function RecentRuns({
  runs,
  onRefresh,
  onSelect,
}: {
  runs: RunPlan[];
  onRefresh: () => void;
  onSelect: (runId: string) => void;
}) {
  return (
    <section className="panel">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-extrabold text-ink">Recent Runs</h2>
        <button className="btn btn-secondary min-h-8 px-3 py-1 text-xs" type="button" onClick={onRefresh}>
          Refresh
        </button>
      </div>
      <div className="mt-3 grid gap-2">
        {runs.length ? (
          runs.slice(0, 8).map((run) => (
            <button
              className="grid gap-1 rounded-md border border-line bg-white p-3 text-left transition hover:border-accent hover:bg-teal-50/50"
              key={run.run_id}
              type="button"
              onClick={() => onSelect(run.run_id)}
            >
              <span className="flex flex-wrap items-center gap-2">
                <b className="text-sm text-ink">{run.run_id}</b>
                <StatusPill tone={statusTone(run.status)}>{run.status}</StatusPill>
                <StatusPill>{run.quality}</StatusPill>
              </span>
              <span className="truncate text-xs text-muted">
                {shortText(run.source_title || run.source, "source", 80)} · {formatSeconds(run.duration)} · {money(run.estimated_cost)}
              </span>
            </button>
          ))
        ) : (
          <p className="hint">No runs yet.</p>
        )}
      </div>
    </section>
  );
}
