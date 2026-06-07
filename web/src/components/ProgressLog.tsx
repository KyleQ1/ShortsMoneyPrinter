export function ProgressLog({ lines }: { lines: string[] }) {
  return (
    <section className="panel">
      <h2 className="text-sm font-extrabold text-ink">Output</h2>
      <pre className="mt-3 min-h-32 max-h-64 overflow-auto rounded-md bg-neutral-900 p-3 text-xs leading-relaxed text-neutral-100">
        {lines.join("\n")}
      </pre>
    </section>
  );
}
