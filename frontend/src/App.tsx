import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { LandingPage } from "./site/LandingPage";

const CinematicIntro = lazy(() => import("./cinematic/CinematicIntro"));

const wasEntered = () => {
  try {
    return sessionStorage.getItem("savant-entered") === "true";
  } catch {
    return false;
  }
};

export function App() {
  const [appReady, setAppReady] = useState(false);
  const [siteMounted, setSiteMounted] = useState(false);
  const [fontsSettled, setFontsSettled] = useState(false);
  const [entered, setEntered] = useState(wasEntered);

  useEffect(() => {
    let cancelled = false;
    const settle = async () => {
      try {
        await document.fonts?.ready;
      } catch {
        /* system font fallback is valid */
      }
      if (!cancelled) setFontsSettled(true);
    };
    void settle();
    const timeout = window.setTimeout(() => {
      if (!cancelled) setFontsSettled(true);
    }, 2500);
    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, []);

  useEffect(() => {
    if (siteMounted && fontsSettled) setAppReady(true);
  }, [fontsSettled, siteMounted]);

  const enter = useCallback(() => {
    try {
      sessionStorage.setItem("savant-entered", "true");
    } catch {
      /* restricted storage must not block entry */
    }
    setEntered(true);
    window.requestAnimationFrame(() =>
      document.getElementById("site-main")?.focus(),
    );
  }, []);

  return (
    <div className="app-shell">
      <LandingPage entered={entered} onReady={() => setSiteMounted(true)} />
      {!entered && (
        <Suspense
          fallback={
            <div className="boot-fallback" role="status" aria-live="polite">
              <span>SAVANT</span>
              <span>Preparing experience…</span>
            </div>
          }
        >
          <CinematicIntro appReady={appReady} onEntered={enter} />
        </Suspense>
      )}
    </div>
  );
}
