import { afterEach, describe, expect, it, vi } from "vitest";
import { approvedLogoExists } from "./assets";
afterEach(() => vi.unstubAllGlobals());
describe("logo asset recovery", () => {
  it("accepts a valid glTF binary response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, {
          status: 200,
          headers: { "content-type": "model/gltf-binary" },
        }),
      ),
    );
    expect(await approvedLogoExists()).toBe(true);
  });
  it("uses fallback for a missing approved asset", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 404 })),
    );
    expect(await approvedLogoExists()).toBe(false);
  });
  it("uses fallback for network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    expect(await approvedLogoExists()).toBe(false);
  });
});
