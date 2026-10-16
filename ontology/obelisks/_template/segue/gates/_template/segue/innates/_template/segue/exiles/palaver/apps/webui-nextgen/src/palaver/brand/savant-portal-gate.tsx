import React, { useEffect, useRef, useState } from "react";
import SavantMark from "./savant-mark";
import "./savant-portal-gate.css";

type Props = { children: React.ReactNode; minimumLoadingMs?: number };
const dockingDuration = 1850;

export default function SavantPortalGate({ children, minimumLoadingMs = 10000 }: Props) {
  const [timeElapsed, setTimeElapsed] = useState(false);
  const [assetsReady, setAssetsReady] = useState(false);
  const [entered, setEntered] = useState(false);
  const [docked, setDocked] = useState(false);
  const mark = useRef<HTMLDivElement>(null);
  const startedAt = useRef(performance.now());
  const animationStarted = useRef(false);

  useEffect(() => {
    const timeout = window.setTimeout(() => setTimeElapsed(true), Math.max(0, minimumLoadingMs - (performance.now() - startedAt.current)));
    return () => window.clearTimeout(timeout);
  }, [minimumLoadingMs]);

  useEffect(() => {
    let cancelled = false;
    const waitForResources = async () => {
      try { if (document.fonts?.ready) await document.fonts.ready; } catch { /* font fallback remains usable */ }
      if (!cancelled) setAssetsReady(true);
    };
    void waitForResources();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!entered || animationStarted.current || !mark.current) return;
    const target = document.getElementById("savant-header-logo-slot");
    const node = mark.current;
    if (!target) return;
    const destination = target.getBoundingClientRect();
    const source = node.getBoundingClientRect();
    if (destination.width <= 0 || destination.height <= 0 || source.width <= 0 || source.height <= 0) return;
    animationStarted.current = true;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dx = destination.left - source.left;
    const dy = destination.top - source.top;
    const sx = destination.width / source.width;
    const sy = destination.height / source.height;
    const animation = node.animate([
      { transform: "translate3d(0,0,0) scale(1,1)" },
      { transform: `translate3d(${dx}px,${dy}px,0) scale(${sx},${sy})` },
    ], { duration: reduced ? 1 : dockingDuration, easing: "cubic-bezier(.16,1,.3,1)", fill: "forwards" });
    void animation.finished.then(() => {
      node.style.left = `${destination.left}px`;
      node.style.top = `${destination.top}px`;
      node.style.width = `${destination.width}px`;
      node.style.height = `${destination.height}px`;
      animation.cancel();
      setDocked(true);
    }).catch(() => { animationStarted.current = false; });
    return () => { animation.cancel(); animationStarted.current = false; };
  }, [entered]);

  const canEnter = timeElapsed && assetsReady;
  return (
    <div className="savant-entry-root" data-docked={docked}>
      <div className="savant-entry-app" aria-hidden={!docked} inert={!docked}>{children}</div>
      <div className="savant-entry-curtain" aria-hidden="true" />
      <div className="savant-entry-logo" ref={mark}>
        <SavantMark mode="header" state="thinking" label="savant" />
      </div>
      {!entered && <div className="savant-entry-action">
        {canEnter
          ? <button type="button" onClick={() => setEntered(true)}>Enter palaver</button>
          : <span role="status" aria-live="polite">Loading palaver</span>}
      </div>}
    </div>
  );
}
