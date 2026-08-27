import { useLayoutEffect } from "react";

interface LandingPageProps {
  entered: boolean;
  onReady?: () => void;
}

export function LandingPage({ entered, onReady }: LandingPageProps) {
  useLayoutEffect(() => {
    onReady?.();
  }, [onReady]);
  return (
    <main
      id="site-main"
      className={`site ${entered ? "site--entered" : ""}`}
      tabIndex={-1}
      aria-hidden={!entered}
    >
      <nav className="site__nav" aria-label="Primary">
        <a className="brand" href="#home">
          SAVANT
        </a>
        <div>
          <a href="#method">Method</a>
          <a href="#contact">Contact</a>
        </div>
      </nav>
      <section id="home" className="site__hero">
        <p className="eyebrow">
          Independent intelligence / engineered experience
        </p>
        <h1>
          Ideas become
          <br />
          <em>worlds.</em>
        </h1>
        <p className="lede">
          Savant creates digital systems where strategy, design, and technology
          move as one.
        </p>
        <a className="site__cta" href="#method">
          Explore the system
        </a>
      </section>
      <section id="method" className="site__section">
        <p className="eyebrow">Our method</p>
        <h2>Observe. Synthesize. Build.</h2>
      </section>
      <footer id="contact">
        <span>SAVANT</span>
        <a href="mailto:hello@savant.example">Begin a conversation</a>
      </footer>
    </main>
  );
}
