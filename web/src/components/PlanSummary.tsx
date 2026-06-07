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
    <section className="panel">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-extrabold text-ink">Plan Summary</h2>
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
    ["1", "Choose the exact model", "API-key models use Replicate. Local uses your Wan command."],
    ["2", "Click Plan", "Creates the timeline, prompts, and cost estimate without provider calls."],
    ["3", "Click Run", "Starts live generation only after the estimate is under your max cost."],
  ];

  return (
    <div className="mt-4 rounded-md border border-dashed border-line bg-white p-5">
      <b className="block text-sm text-ink">No video planned yet</b>
      <p className="mt-1 text-sm text-muted">Paste a YouTube, Instagram, TikTok URL, or local file path to preview cost before spending credits.</p>
      <div className="mt-4 grid gap-3">
        {steps.map(([number, title, body]) => (
          <div className="grid grid-cols-[24px_minmax(0,1fr)] gap-3" key={number}>
            <span className="grid h-6 w-6 place-items-center rounded-full bg-teal-50 text-xs font-extrabold text-accent">{number}</span>
            <div>
              <b className="block text-sm text-ink">{title}</b>
              <small className="text-xs text-muted">{body}</small>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PlanDetails({ plan, maxCost }: { plan: RunPlan; maxCost: number }) {
  const costTone = maxCost > 0 && plan.estimated_cost > maxCost ? "bad" : "good";
  const costNote =
    maxCost <= 0
      ? "Set max cost before Run"
      : plan.estimated_cost > maxCost
        ? `Over cap by ${money(plan.estimated_cost - maxCost)}`
        : "Ready for Run";
  const sourceName = plan.source_title || plan.source || plan.source_platform || "source";

  return (
    <div className="mt-4 grid gap-4">
      <div className="grid overflow-hidden rounded-md border border-line bg-white md:grid-cols-[minmax(180px,0.85fr)_minmax(0,1.15fr)]">
        <div className="bg-accent p-5 text-white">
          <span className="text-xs font-bold uppercase tracking-normal opacity-85">Estimated Cost</span>
          <b className="mt-1 block text-4xl font-black leading-none">{money(plan.estimated_cost)}</b>
          <small className="mt-2 block text-xs font-semibold opacity-85">
            {formatSeconds(plan.duration)} · {plan.block_count} block{plan.block_count === 1 ? "" : "s"}
          </small>
          <span className="mt-3 inline-flex rounded-full bg-white px-2.5 py-1 text-xs font-extrabold text-accent">{costNote}</span>
        </div>
        <div className="grid bg-line md:grid-cols-2">
          <Fact label="Source" value={sourceName} title={sourceName} />
          <Fact label="Model" value={plan.model_label} />
          <Fact label="Generation" value={`${plan.resolution} · ${plan.mode}`} />
          <Fact label="Source Audio" value={plan.has_audio ? "Detected" : "None"} />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <StatusPill>Platform: {plan.source_platform || "local"}</StatusPill>
        <StatusPill>Original: {formatSeconds(plan.original_duration || plan.duration)}</StatusPill>
        <StatusPill>Aspect: {plan.aspect_ratio || `${plan.width}x${plan.height}`}</StatusPill>
        <StatusPill tone={costTone}>Max cost: {maxCost > 0 ? money(maxCost) : "not set"}</StatusPill>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between gap-3">
          <h3 className="text-sm font-extrabold text-ink">Block Timeline</h3>
          <span className="text-xs text-muted">{plan.block_count} total</span>
        </div>
        <div className="grid gap-2">
          {plan.blocks.length ? (
            plan.blocks.map((block) => (
              <div className="grid gap-3 rounded-md border border-line bg-white p-3 sm:grid-cols-[96px_minmax(0,1fr)_80px]" key={block.index}>
                <div className="text-xs tabular-nums text-muted">
                  {block.start.toFixed(1)}-{block.end.toFixed(1)}s
                </div>
                <div className="min-w-0">
                  <b className="flex flex-wrap items-center gap-2 text-sm text-ink">
                    Block {String(block.index).padStart(3, "0")}
                    <StatusPill tone={statusTone(block.status)}>{block.status}</StatusPill>
                  </b>
                  <code className="mt-1 block max-h-16 overflow-hidden whitespace-pre-wrap break-words text-xs text-muted">
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
    <div className="min-w-0 bg-white p-3" title={title}>
      <b className="block truncate text-sm text-ink">{value}</b>
      <span className="mt-0.5 block text-xs text-muted">{label}</span>
    </div>
  );
}
