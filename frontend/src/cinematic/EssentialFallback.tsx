interface Props {
  complete: boolean;
  appReady: boolean;
  error?: string | null;
  onEnter: () => void;
  onRetry: () => void;
}
export function EssentialFallback({
  complete,
  appReady,
  error,
  onEnter,
  onRetry,
}: Props) {
  const entrySafe = (complete && appReady) || Boolean(error);
  return (
    <div
      className="essential-fallback"
      role="group"
      aria-label="Savant essential introduction"
    >
      <div className="fallback-signal" aria-hidden="true" />
      <div className="fallback-wordmark">SAVANT</div>
      {error && (
        <p role="alert">
          The cinematic renderer could not start. The site remains available.
        </p>
      )}
      <div className="fallback-actions">
        {entrySafe && (
          <button className="enter-savant" onClick={onEnter}>
            ENTER SAVANT
          </button>
        )}
        {error && (
          <button className="secondary-control" onClick={onRetry}>
            Retry cinematic
          </button>
        )}
      </div>
    </div>
  );
}
