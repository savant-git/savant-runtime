import { describe, expect, it } from "vitest";
import type { Capabilities, CinematicState } from "../types";
import { canEnter, cinematicReducer, initialState } from "./machine";

const capabilities: Capabilities = {
  webgl2: true,
  webgpu: false,
  reducedMotion: false,
  hardwareConcurrency: 8,
  deviceMemory: 8,
  maxTextureSize: 16384,
  dpr: 1,
  touch: false,
};
const reduce = (
  events: Parameters<typeof cinematicReducer>[1][],
  start: CinematicState = initialState,
) => events.reduce(cinematicReducer, start);
const readyToPlay = () =>
  reduce([
    { type: "BOOT" },
    { type: "CAPABILITIES", capabilities, quality: "standard" },
    { type: "ASSETS_READY" },
  ]);

describe("cinematic startup state machine", () => {
  it("runs the startup states in order", () => {
    expect(readyToPlay().phase).toBe("readyToPlay");
  });
  it("does not play before assets settle", () => {
    const state = reduce([{ type: "BOOT" }, { type: "PLAY" }]);
    expect(state.phase).toBe("capabilityCheck");
  });
  it("tracks application readiness before completion without exposing entry", () => {
    const state = reduce(
      [{ type: "APP_READY" }, { type: "PLAY" }],
      readyToPlay(),
    );
    expect(state.appReady).toBe(true);
    expect(canEnter(state)).toBe(false);
  });
  it("waits for app readiness when cinematic completes first", () => {
    const state = reduce(
      [{ type: "PLAY" }, { type: "COMPLETE" }],
      readyToPlay(),
    );
    expect(state.phase).toBe("cinematicComplete");
    expect(canEnter(state)).toBe(false);
  });
  it("enters awaitingEntry when application becomes ready later", () => {
    const state = reduce(
      [{ type: "PLAY" }, { type: "COMPLETE" }, { type: "APP_READY" }],
      readyToPlay(),
    );
    expect(state.phase).toBe("awaitingEntry");
    expect(canEnter(state)).toBe(true);
  });
  it("enters awaitingEntry when app was ready first", () => {
    const state = reduce(
      [{ type: "APP_READY" }, { type: "PLAY" }, { type: "COMPLETE" }],
      readyToPlay(),
    );
    expect(state.phase).toBe("awaitingEntry");
  });
  it("prevents entry before both readiness gates", () => {
    expect(
      cinematicReducer(readyToPlay(), { type: "ENTER" }).entryRequested,
    ).toBe(false);
  });
  it("prevents repeated activation", () => {
    const ready = reduce(
      [{ type: "APP_READY" }, { type: "PLAY" }, { type: "COMPLETE" }],
      readyToPlay(),
    );
    const first = cinematicReducer(ready, { type: "ENTER" }),
      second = cinematicReducer(first, { type: "ENTER" });
    expect(first.phase).toBe("transitioning");
    expect(second).toEqual(first);
  });
  it("finishes transition exactly from transitioning", () => {
    const ready = reduce(
      [
        { type: "APP_READY" },
        { type: "PLAY" },
        { type: "COMPLETE" },
        { type: "ENTER" },
        { type: "ENTERED" },
      ],
      readyToPlay(),
    );
    expect(ready.phase).toBe("entered");
  });
  it("records skip without faking completion", () => {
    const state = cinematicReducer(readyToPlay(), { type: "SKIP" });
    expect(state.skipped).toBe(true);
    expect(state.cinematicComplete).toBe(false);
  });
  it("supports reduced-motion capabilities", () => {
    const state = reduce([
      { type: "BOOT" },
      {
        type: "CAPABILITIES",
        capabilities: { ...capabilities, reducedMotion: true },
        quality: "mobile",
      },
    ]);
    expect(state.capabilities?.reducedMotion).toBe(true);
    expect(state.quality).toBe("mobile");
  });
  it("allows a one-way quality downgrade but never an upgrade", () => {
    const standard = cinematicReducer(readyToPlay(), {
      type: "DOWNGRADE_QUALITY",
      quality: "mobile",
    });
    expect(standard.quality).toBe("mobile");
    expect(
      cinematicReducer(standard, {
        type: "DOWNGRADE_QUALITY",
        quality: "ultra",
      }).quality,
    ).toBe("mobile");
  });
  it("provides recoverable renderer failure", () => {
    const state = cinematicReducer(readyToPlay(), {
      type: "FAIL",
      error: "context lost",
    });
    expect(state.phase).toBe("recoverableError");
    expect(state.error).toBe("context lost");
  });
  it("retries without losing application readiness", () => {
    const failed = reduce(
      [{ type: "APP_READY" }, { type: "FAIL", error: "asset" }],
      readyToPlay(),
    );
    const state = cinematicReducer(failed, { type: "RETRY" });
    expect(state.phase).toBe("capabilityCheck");
    expect(state.appReady).toBe(true);
  });
  it("offers finite direct-entry recovery", () => {
    const state = cinematicReducer(initialState, { type: "DIRECT_ENTRY" });
    expect(state.phase).toBe("transitioning");
    expect(state.appReady && state.cinematicComplete).toBe(true);
  });
  it("keeps progress monotonic and bounded", () => {
    const state = reduce(
      [
        { type: "PROGRESS", progress: 0.8 },
        { type: "PROGRESS", progress: 0.2 },
        { type: "PROGRESS", progress: 2 },
      ],
      readyToPlay(),
    );
    expect(state.progress).toBe(1);
  });
  it("clears transient failure state on retry", () => {
    const failed = cinematicReducer(initialState, {
      type: "FAIL",
      error: "missing logo",
    });
    expect(cinematicReducer(failed, { type: "RETRY" }).error).toBeNull();
  });
});
