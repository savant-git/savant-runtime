import gsap from "gsap";
import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";
import { approvedLogoExists } from "./config/assets";
import { CINEMATIC } from "./config/cinematic";
import { CinematicAudioController } from "./audio/CinematicAudioController";
import { detectCapabilities } from "./capability/detectCapabilities";
import { CinematicDebugPanel } from "./debug/CinematicDebugPanel";
import { CinematicErrorBoundary } from "./CinematicErrorBoundary";
import { EssentialFallback } from "./EssentialFallback";
import { usePageVisibility } from "./hooks/usePageVisibility";
import { selectQualityTier } from "./quality/selectQualityTier";
import { canEnter, cinematicReducer, initialState } from "./state/machine";
import { createMasterTimeline } from "./timeline/createMasterTimeline";
import { useEntryTransition } from "./transition/useEntryTransition";

const CinematicCanvas = lazy(() => import("./CinematicCanvas"));
interface Props {
  appReady: boolean;
  onEntered: () => void;
}

export default function CinematicIntro({ appReady, onEntered }: Props) {
  const [state, dispatch] = useReducer(cinematicReducer, initialState),
    [logoAvailable, setLogoAvailable] = useState(false),
    root = useRef<HTMLDivElement>(null),
    playhead = useRef({ time: 0 }),
    time = useRef(0),
    timeline = useRef<gsap.core.Timeline | null>(null),
    audio = useMemo(() => new CinematicAudioController(), []),
    act = useRef(""),
    timelineStarted = useRef(false);
  useEffect(() => {
    dispatch({ type: "BOOT" });
    const capabilities = detectCapabilities();
    dispatch({
      type: "CAPABILITIES",
      capabilities,
      quality: selectQualityTier(capabilities),
    });
    const controller = new AbortController();
    const timeout = window.setTimeout(
      () => controller.abort(),
      CINEMATIC.assetTimeoutMs,
    );
    approvedLogoExists(controller.signal)
      .then(setLogoAvailable)
      .finally(() => dispatch({ type: "ASSETS_READY" }));
    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, []);
  useEffect(() => {
    if (appReady) dispatch({ type: "APP_READY" });
  }, [appReady]);
  useEffect(() => {
    if (!state.assetsReady || !state.capabilities || timelineStarted.current)
      return;
    timelineStarted.current = true;
    dispatch({ type: "PLAY" });
    timeline.current = createMasterTimeline(playhead.current, {
      reducedMotion: state.capabilities.reducedMotion,
      onProgress: (progress) => {
        time.current = playhead.current.time;
        dispatch({ type: "PROGRESS", progress });
        const t = time.current;
        const next =
          t < 3.1
            ? "signal"
            : t < 7.1
              ? "fracture"
              : t < 12.1
                ? "awakening"
                : t < 16.2
                  ? "forge"
                  : "recognition";
        if (next !== act.current) {
          act.current = next;
          audio.cue(next);
        }
      },
      onComplete: () => dispatch({ type: "COMPLETE" }),
    });
    timeline.current.play();
    return () => {
      timeline.current?.kill();
      timeline.current = null;
      timelineStarted.current = false;
    };
  }, [audio, state.assetsReady, state.capabilities]);
  useEffect(() => () => audio.dispose(), [audio]);
  usePageVisibility(timeline);
  const finish = useCallback(() => {
    dispatch({ type: "ENTERED" });
    onEntered();
  }, [onEntered]);
  useEntryTransition(state.phase === "transitioning", root, finish);
  const enter = useCallback(() => dispatch({ type: "ENTER" }), []),
    directEnter = useCallback(() => dispatch({ type: "DIRECT_ENTRY" }), []),
    retry = useCallback(() => location.reload(), []);
  const toggleSound = async () => {
    try {
      if (state.muted) {
        await audio.enable();
        audio.mute(false);
      } else {
        audio.mute(true);
      }
      dispatch({ type: "TOGGLE_SOUND" });
    } catch {
      audio.mute(true);
    }
  };
  const skip = () => {
    dispatch({ type: "SKIP" });
    timeline.current?.progress(1);
  };
  const rendererError = (message: string) =>
    dispatch({ type: "FAIL", error: message });
  const essential =
    state.quality === "essential" || state.phase === "recoverableError";
  return (
    <div
      ref={root}
      className={`cinematic-intro ${state.phase === "awaitingEntry" ? "cinematic-intro--ready" : ""}`}
      aria-label="Savant cinematic introduction"
    >
      {essential ? (
        <EssentialFallback
          complete={
            state.cinematicComplete || state.phase === "recoverableError"
          }
          appReady={state.appReady}
          error={state.error}
          onEnter={state.phase === "recoverableError" ? directEnter : enter}
          onRetry={retry}
        />
      ) : (
        <CinematicErrorBoundary
          onError={(e) => rendererError(e.message)}
          fallback={(e) => (
            <EssentialFallback
              complete
              appReady={state.appReady}
              error={e.message}
              onEnter={directEnter}
              onRetry={retry}
            />
          )}
        >
          <Suspense
            fallback={
              <div className="cinematic-loading" role="status">
                Forming the signal…
              </div>
            }
          >
            <CinematicCanvas
              time={time}
              qualityTier={state.quality}
              reducedMotion={state.capabilities?.reducedMotion ?? false}
              logoAvailable={logoAvailable}
              onRendererReady={() => undefined}
              onRendererError={rendererError}
              onQualityDowngrade={(quality) =>
                dispatch({ type: "DOWNGRADE_QUALITY", quality })
              }
            />
          </Suspense>
        </CinematicErrorBoundary>
      )}
      <div className="cinematic-grade" />
      <div className="cinematic-grain" />
      <div
        className={`final-identity ${state.progress > 0.87 ? "final-identity--visible" : ""}`}
        aria-hidden={state.progress <= 0.87}
      >
        <span className="final-identity__word">SAVANT</span>
        {!logoAvailable && import.meta.env.DEV && (
          <small>development fallback — approved logo pending</small>
        )}
      </div>
      <div className="cinematic-controls">
        <button
          className="sound-control"
          onClick={toggleSound}
          aria-pressed={!state.muted}
        >
          {state.muted ? "Enable sound" : "Sound on"}
        </button>
        {state.progress >= CINEMATIC.skipAvailableAt / CINEMATIC.duration &&
          !state.cinematicComplete && (
            <button className="skip-control" onClick={skip}>
              Skip intro
            </button>
          )}
      </div>
      {canEnter(state) && (
        <button className="enter-savant" onClick={enter} autoFocus>
          <span>ENTER SAVANT</span>
        </button>
      )}
      {state.phase === "cinematicComplete" && !state.appReady && (
        <div className="readiness-hold" role="status">
          Finalizing Savant…
        </div>
      )}
      <div
        className="cinematic-progress"
        role="progressbar"
        aria-label="Cinematic progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(state.progress * 100)}
      >
        <span style={{ transform: `scaleX(${state.progress})` }} />
      </div>
      <CinematicDebugPanel
        state={state}
        onJump={(t) => {
          playhead.current.time = t;
          time.current = t;
          timeline.current?.progress(t / CINEMATIC.duration);
        }}
        onPause={() => {
          const value = timeline.current;
          if (value) value.paused(!value.paused());
        }}
        onReplay={() => timeline.current?.restart()}
      />
    </div>
  );
}
