import type { RunPlan } from "../types";

export function OutputPreview({ plan }: { plan: RunPlan | null }) {
  if (!plan?.final_path || plan.status !== "done") return null;

  const src = `/api/runs/${plan.run_id}/final.mp4`;
  return (
    <section className="panel animate-fade-up">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="grid h-6 w-6 place-items-center rounded-md bg-success/15 text-success">
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
          </span>
          <h2 className="text-base font-extrabold tracking-tight text-ink">Your Short is ready</h2>
        </div>
        <a
          className="btn min-h-9 px-3 py-1.5 text-xs"
          href={src}
          download
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v12m0 0 4-4m-4 4-4-4M4 21h16" /></svg>
          Download MP4
        </a>
      </div>
      <div className="mt-4 grid place-items-center rounded-xl border border-line bg-black p-3">
        <video className="max-h-[520px] w-auto rounded-lg" controls src={src} />
      </div>
      <p className="mt-3 truncate font-mono text-xs text-faint" title={plan.run_dir}>
        {plan.run_dir}
      </p>
    </section>
  );
}
