let credential = "";
export function setCredential(value: string) {
  credential = value;
}
export async function api<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const headers: Record<string, string> = { "X-DemandSense-Token": credential };
  if (body !== undefined) {
    headers["Idempotency-Key"] = crypto.randomUUID();
    if (!(body instanceof FormData))
      headers["Content-Type"] = "application/json";
  }
  const response = await fetch("/api/v1" + path, {
    method: body === undefined ? "GET" : "POST",
    headers,
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(
      data?.error?.message ?? `Request failed (${response.status})`,
    );
  }
  return response.json();
}
export async function exportForecast(runId: string) {
  const response = await fetch(`/api/v1/runs/${runId}/export`, {
    headers: { "X-DemandSense-Token": credential },
  });
  if (!response.ok) throw new Error("Export failed");
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = `forecast-${runId}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
export const num = (v: number | null | undefined, digits = 0) =>
  v == null
    ? "—"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(
        v,
      );
export const pct = (v: number | null | undefined) =>
  v == null ? "Undefined" : `${(v * 100).toFixed(1)}%`;
export const title = (v: string) =>
  v.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
