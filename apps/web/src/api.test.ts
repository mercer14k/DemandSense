import { afterEach, describe, expect, it, vi } from "vitest";
import { api, num, pct, setCredential } from "./api";
afterEach(() => vi.unstubAllGlobals());
describe("Display semantics", () => {
  it("does not turn undefined metrics into perfect scores", () => {
    expect(pct(null)).toBe("Undefined");
    expect(num(null)).toBe("—");
    expect(pct(0)).toBe("0.0%");
  });
  it("shows signed bias", () => {
    expect(pct(-0.123)).toBe("-12.3%");
  });
});
describe("API boundaries", () => {
  it("sends authorization and a unique mutation key", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ id: "run" }) });
    vi.stubGlobal("fetch", fetcher);
    setCredential("test");
    await api("/runs", { sku: "test" });
    const config = fetcher.mock.calls[0][1];
    expect(config.headers["X-DemandSense-Token"]).toBe("test");
    expect(config.headers["Idempotency-Key"]).toBeTruthy();
    expect(config.method).toBe("POST");
  });
  it("surfaces server validation errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue({
          ok: false,
          status: 422,
          json: async () => ({ error: { message: "Daily series has gaps" } }),
        }),
    );
    await expect(api("/runs", {})).rejects.toThrow("Daily series has gaps");
  });
});
