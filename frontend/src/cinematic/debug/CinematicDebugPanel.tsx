import type { CinematicState } from "../types";
export function CinematicDebugPanel({
  state,
  onJump,
  onPause,
  onReplay,
}: {
  state: CinematicState;
  onJump: (time: number) => void;
  onPause: () => void;
  onReplay: () => void;
}) {
  if (
    !import.meta.env.DEV ||
    !new URLSearchParams(location.search).has("cinematicDebug")
  )
    return null;
  return (
    <aside className="cinematic-debug">
      <strong>Cinematic debug</strong>
      <span>
        {state.phase} / {state.quality}
      </span>
      <span>{Math.round(state.progress * 100)}%</span>
      <div>
        {[0, 3.1, 7.1, 12.1, 16.2].map((t) => (
          <button key={t} onClick={() => onJump(t)}>
            {t}s
          </button>
        ))}
      </div>
      <button onClick={onPause}>Pause/resume</button>
      <button onClick={onReplay}>Replay</button>
    </aside>
  );
}
