import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import SavantMark from "./savant-mark";
import "./savant-portal-gate.css";

type Props = { children: React.ReactNode; minimumLoadingMs?: number };
const travelMs = 1850;
export default function SavantPortalGate({ children, minimumLoadingMs = 10000 }: Props) {
  const [portal, setPortal] = useState<HTMLElement | null>(null);
  const [ready, setReady] = useState(false);
  const [entered, setEntered] = useState(false);
  const [docked, setDocked] = useState(false);
  const markRef = useRef<HTMLDivElement>(null);
  const started = useRef(performance.now());
  const moving = useRef(false);
  useLayoutEffect(() => {
    const node = document.createElement("div");
    node.id = "savant-independent-gate";
    document.body.appendChild(node);
    setPortal(node);
    return () => { node.remove(); };
  }, []);
  useEffect(() => {
    const previous = document.body.style.overflow;
    if (!docked) document.body.style.overflow = "hidden";
    else document.body.style.overflow = previous;
    return () => { document.body.style.overflow = previous; };
  }, [docked]);
  useEffect(() => {
    const wait = Math.max(0, minimumLoadingMs - (performance.now() - started.current));
    const id = window.setTimeout(() => setReady(true), wait);
    return () => window.clearTimeout(id);
  }, [minimumLoadingMs]);
  useEffect(() => {
    if (!entered || moving.current || !markRef.current) return;
    const target = document.getElementById("savant-header-logo-slot");
    if (!target) return;
    const rect = target.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    moving.current = true;
    const element = markRef.current;
    const from = element.getBoundingClientRect();
    const dx = rect.left - from.left;
    const dy = rect.top - from.top;
    const sx = rect.width / from.width;
    const sy = rect.height / from.height;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const animation = element.animate([
      { transform: "translate3d(0,0,0) scale(1,1)" },
      { transform: `translate3d(${dx}px,${dy}px,0) scale(${sx},${sy})` }
    ], { duration: reduced ? 1 : travelMs, easing: "cubic-bezier(.16,1,.3,1)", fill: "forwards" });
    animation.finished.then(() => {
      element.style.left = `${rect.left}px`;
      element.style.top = `${rect.top}px`;
      element.style.width = `${rect.width}px`;
      element.style.height = `${rect.height}px`;
      animation.cancel();
      setDocked(true);
    }).catch(() => { moving.current = false; });
    return () => { animation.cancel(); moving.current = false; };
  }, [entered, portal]);
  return <>
    <div className="savant-gate-app" data-open={docked} aria-hidden={!docked} inert={!docked}>{children}</div>
    {portal && createPortal(<div className="savant-gate-layer" data-open={docked}>
      <div className="savant-gate-background" />
      <div className="savant-gate-logo" ref={markRef}>
        <SavantMark mode="header" state="thinking" label="savant" />
      </div>
      {!entered && <div className="savant-gate-action">
        {ready ? <button type="button" onClick={() => setEntered(true)}>Enter palaver</button> : <span>Loading palaver</span>}
      </div>}
    </div>, portal)}
  </>;
}
