import { useState } from "react";
import { systems } from "../data/missions.js";

export default function SystemGrid() {
  const [active, setActive] = useState("orion");

  return (
    <div className="system-grid">
      {systems.map(system => {
        const selected = active === system.id;

        return (
          <button
            key={system.id}
            className={
              selected
                ? "system-card active"
                : "system-card"
            }
            onClick={() => setActive(system.id)}
          >
            <div className="system-card-top">
              <span>{system.index}</span>

              <small>
                {selected ? "FOCUSED" : "EXPLORE"}
              </small>
            </div>

            <div className="system-symbol">
              <span>
                {system.shortName
                  .slice(0, 2)}
              </span>

              <i />
              <i />
            </div>

            <div className="system-card-copy">
              <small>{system.type}</small>

              <h3>{system.name}</h3>

              <p>{system.description}</p>
            </div>

            <span className="system-arrow">↗</span>
          </button>
        );
      })}
    </div>
  );
}
