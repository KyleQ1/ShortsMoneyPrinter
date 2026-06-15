import { formatSeconds, money, shortText } from "../lib";
import type { RunPlan } from "../types";
import { StatusPill, statusTone } from "./StatusPill";

type PlanSummaryProps = {
  plan: RunPlan | null;
  maxCost: number;
  planning: boolean;
  activityLabel: string;
};

export function PlanSummary({ plan, maxCost, planning, activityLabel }: PlanSummaryProps) {
  return (
    <section className="panel animate-fade-up">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-extrabold tracking-tight text-ink">Plan Summary</h2>
        <div className="flex items-center gap-2">
          {activityLabel ? (
            <span className="inline-flex items-center gap-2 text-xs font-bold text-muted" aria-live="polite">
              {planning ? <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line border-t-accent" /> : null}
              {activityLabel}
            </span>
          ) : null}
          <StatusPill tone={plan ? statusTone(plan.status) : "neutral"}>{plan?.status || "No plan"}</StatusPill>
        </div>
      </div>

      {plan ? <PlanDetails plan={plan} maxCost={maxCost} /> : <EmptyPlan />}
    </section>
  );
}

function EmptyPlan() {
  const steps = [
    ["Drop in a video", "Paste a public YouTube, Instagram, or TikTok URL — or a local MP4 path."],
    ["Plan it — free", "Builds the timeline, prompts, and a cost estimate without any provider calls."],
    ["Run when ready", "Generation starts only once the estimate is under your max cost and you confirm."],
  ];

  return (
    <div className="mt-5 rounded-xl border border-dashed border-line bg-surface-2/30 p-6">
      <div className="mb-5 flex flex-col items-center text-center">
        <span className="grid h-12 w-12 place-items-center rounded-2xl bg-accent-soft/50 text-accent">
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 9h18M8 4v5" /><path d="m11 13 4 2.5-4 2.5z" fill="currentColor" />
          </svg>
        </span>
        <p className="mt-3 text-sm font-semibold text-ink">No plan yet</p>
        <p className="mt-1 text-xs text-muted">Fill in a source on the left and hit Plan to see the timeline and cost.</p>
      </div>
      <div className="grid gap-3">
        {steps.map(([title, body], i) => (
          <div className="flex gap-3" key={title}>
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent-gradient text-xs font-extrabold text-white">{i + 1}</span>
            <div>
              <b className="block text-sm text-ink">{title}</b>
              <small className="text-xs leading-relaxed text-muted">{body}</small>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PlanDetails({ plan, maxCost }: { plan: RunPlan; maxCost: number }) {
  const overCap = maxCost > 0 && plan.estimated_cost > maxCost;
  const costNote = maxCost <= 0 ? "Set max cost before Run" : overCap ? `Over cap by ${money(plan.estimated_cost - maxCost)}` : "Ready for Run";
  const sourceName = plan.source_title || plan.source || plan.source_platform || "source";
  const done = plan.blocks.filter((b) => b.status === "done" || b.status === "skipped").length;
  const pct = plan.block_count ? Math.round((done / plan.block_count) * 100) : 0;
  const isRunning = plan.status === "running";

  return (
    <div className="mt-5 grid gap-4">
      {plan.status === "failed" && plan.error ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 p-3.5">
          <b className="block text-sm text-danger">Run failed</b>
          <p className="mt-1 text-xs text-danger/90">{plan.error}</p>
        </div>
      ) : null}

      {/* Cost hero + facts */}
      <div className="grid overflow-hidden rounded-xl border border-line md:grid-cols-[minmax(190px,0.8fr)_minmax(0,1.2fr)]">
        <div className="relative overflow-hidden bg-accent-gradient p-5 text-white">
          <span className="text-xs font-bold uppercase tracking-wider opacity-80">Estimated cost</span>
          <b className="mt-1 block text-[2.75rem] font-black leading-none">{money(plan.estimated_cost)}</b>
          <small className="mt-2 block text-xs font-semibold opacity-80">
            {formatSeconds(plan.duration)} · {plan.block_count} block{plan.block_count === 1 ? "" : "s"}
          </small>
          <span
            className={
              "mt-3 inline-flex items-center gap-1.5 rounded-full bg-night/90 px-2.5 py-1 text-xs font-extrabold " +
              (overCap ? "text-danger" : "text-success")
            }
          >
            <span className={"h-1.5 w-1.5 rounded-full " + (overCap ? "bg-danger" : "bg-success")} />
            {costNote}
          </span>
        </div>
        <div className="grid bg-surface-2/40 sm:grid-cols-2">
          <Fact label="Source" value={sourceName} title={sourceName} />
          <Fact label="Model" value={plan.model_label} />
          <Fact label="Output" value={`${plan.resolution} · ${plan.mode}`} />
          <Fact
            label="Audio"
            value={plan.audio_mode === "tts" ? "TTS" : plan.audio_mode === "source" ? (plan.has_audio ? "Original" : "None") : "None"}
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <StatusPill>Platform · {plan.source_platform || "local"}</StatusPill>
        <StatusPill>Language · {plan.language}</StatusPill>
        <StatusPill>Original · {formatSeconds(plan.original_duration || plan.duration)}</StatusPill>
        <StatusPill>Aspect · {plan.aspect_ratio || `${plan.width}x${plan.height}`}</StatusPill>
        <StatusPill tone={overCap ? "bad" : "good"}>Max cost · {maxCost > 0 ? money(maxCost) : "not set"}</StatusPill>
      </div>

      {/* Progress bar while running / done */}
      {(isRunning || plan.status === "done") && plan.block_count ? (
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs font-semibold text-muted">
            <span>{plan.status === "done" ? "Complete" : "Generating…"}</span>
            <span className="tabular-nums">
              {done}/{plan.block_count} · {pct}%
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-3">
            <div
              className="h-full rounded-full bg-accent-gradient transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      ) : null}

      {/* Timeline */}
      <div>
        <div className="mb-2 flex items-center justify-between gap-3">
          <h3 className="section-title">Block timeline</h3>
          <span className="text-xs text-faint">{plan.block_count} total</span>
        </div>
        <div className="grid gap-2">
          {plan.blocks.length ? (
            plan.blocks.map((block) => (
              <div
                className="grid items-center gap-3 rounded-xl border border-line bg-surface-2/40 p-3 sm:grid-cols-[88px_minmax(0,1fr)_72px]"
                key={block.index}
              >
                <div className="font-mono text-xs tabular-nums text-faint">
                  {block.start.toFixed(1)}–{block.end.toFixed(1)}s
                </div>
                <div className="min-w-0">
                  <span className="flex flex-wrap items-center gap-2 text-sm font-semibold text-ink">
                    Block {String(block.index).padStart(3, "0")}
                    <StatusPill tone={statusTone(block.status)}>{block.status}</StatusPill>
                  </span>
                  <code className="mt-1 block max-h-12 overflow-hidden whitespace-pre-wrap break-words font-mono text-xs text-muted">
                    {shortText(block.prompt, "Prompt pending")}
                  </code>
                  {block.error ? <p className="mt-1 text-xs font-semibold text-danger">{block.error}</p> : null}
                </div>
                <div className="text-sm font-extrabold tabular-nums text-ink sm:text-right">{money(block.estimated_cost)}</div>
              </div>
            ))
          ) : (
            <p className="hint">No blocks planned yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Fact({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <div className="min-w-0 border-b border-line/60 p-3.5 [&:nth-child(odd)]:sm:border-r" title={title}>
      <span className="block text-[11px] font-semibold uppercase tracking-wider text-faint">{label}</span>
      <b className="mt-0.5 block truncate text-sm text-ink">{value}</b>
    </div>
  );
}
