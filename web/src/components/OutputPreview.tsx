import type { RunPlan } from "../types";

export function OutputPreview({ plan }: { plan: RunPlan | null }) {
  if (!plan?.final_path || plan.status !== "done") return null;

  const src = `/api/runs/${plan.run_id}/final.mp4`;
  return (
    <section className="panel">
      <h2 className="text-sm font-extrabold text-ink">Final MP4</h2>
      <video className="mt-3 max-h-[480px] w-full rounded-md bg-neutral-950" controls src={src} />
      <p className="mt-3">
        <a className="font-bold text-accent hover:text-teal-800" href={src}>
          Download final MP4
        </a>
      </p>
      <p className="mt-1 text-xs text-muted">Run folder: {plan.run_dir}</p>
    </section>
  );
}
