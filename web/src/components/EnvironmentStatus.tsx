import type { PreflightStatus } from "../types";
import { StatusPill } from "./StatusPill";

export function EnvironmentStatus({ status }: { status: PreflightStatus | null }) {
  const checks = status
    ? [
        ["ffmpeg", status.ffmpeg, "ffmpeg"],
        ["ffprobe", status.ffprobe, "ffprobe"],
        ["yt-dlp", status.yt_dlp, "URL download"],
        ["Replicate token", status.replicate_token, "Run"],
        ["Replicate package", status.replicate_package, "Run"],
      ]
    : [];

  return (
    <section className="panel">
      <h2 className="text-sm font-extrabold text-ink">Environment</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {status ? (
          checks.map(([label, ok, hint]) => (
            <StatusPill key={String(label)} tone={ok ? "good" : "warn"} className="cursor-help" title={String(hint)}>
              {ok ? "OK" : "Missing"}: {label}
            </StatusPill>
          ))
        ) : (
          <StatusPill tone="warn">Checking environment</StatusPill>
        )}
      </div>
    </section>
  );
}
