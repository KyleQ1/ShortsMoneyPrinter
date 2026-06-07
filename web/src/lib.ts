export function money(value: number | null | undefined): string {
  return `$${Number(value || 0).toFixed(2)}`;
}

export function shortText(value: string | null | undefined, fallback = "None", limit = 96): string {
  const text = String(value || fallback);
  return text.length > limit ? `${text.slice(0, limit - 3)}...` : text;
}

export function parseUsd(value: string): number {
  return Number(value.replace(/[^0-9.]/g, "") || 0);
}

export function formatSeconds(value: number | null | undefined): string {
  return `${Number(value || 0).toFixed(1)}s`;
}

export function classNames(...items: Array<string | false | null | undefined>): string {
  return items.filter(Boolean).join(" ");
}
