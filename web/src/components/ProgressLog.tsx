export function ProgressLog({ lines }: { lines: string[] }) {
  return (
    <section className="panel animate-fade-up">
      <div className="flex items-center gap-2">
        <span className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-danger/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-success/70" />
        </span>
        <h2 className="section-title">Activity log</h2>
      </div>
      <div className="relative mt-3 overflow-hidden rounded-xl border border-line bg-[#06070b]">
        <pre className="max-h-72 min-h-32 overflow-auto p-4 font-mono text-xs leading-relaxed text-emerald-200/90">
          {lines.map((line, i) => (
            <div key={i} className="whitespace-pre-wrap break-words">
              <span className="select-none text-faint">{String(i + 1).padStart(2, "0")} </span>
              {line}
            </div>
          ))}
        </pre>
      </div>
    </section>
  );
}
