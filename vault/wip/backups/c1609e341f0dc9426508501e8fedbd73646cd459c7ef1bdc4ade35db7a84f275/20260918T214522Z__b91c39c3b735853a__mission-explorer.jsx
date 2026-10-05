import { useState } from "react";
import { missions } from "../data/missions.js";

export default function MissionExplorer() {
  const [selected, setSelected] = useState(0);

  const mission = missions[selected];

  return (
    <div className="mission-explorer">
      <div
        className="mission-tabs"
        role="tablist"
        aria-label="Artemis missions"
      >
        {missions.map((item, index) => (
          <button
            key={item.id}
            className={
              selected === index
                ? "mission-tab active"
                : "mission-tab"
            }
            onClick={() => setSelected(index)}
            role="tab"
            aria-selected={selected === index}
          >
            <span>{item.numeral}</span>
            <small>{item.year}</small>
          </button>
        ))}
      </div>

      <div
        className="mission-display"
        key={mission.id}
      >
        <div className="mission-number">
          <span>ARTEMIS</span>
          <strong>{mission.numeral}</strong>
        </div>

        <div className="mission-content">
          <div className="mission-status">
            <span
              className={
                mission.status === "COMPLETE"
                  ? "complete"
                  : ""
              }
            />

            {mission.status}
          </div>

          <h3>{mission.title}</h3>

          <p>{mission.description}</p>

          <div className="mission-facts">
            <div>
              <small>DESTINATION</small>
              <strong>{mission.destination}</strong>
            </div>

            <div>
              <small>CREW</small>
              <strong>{mission.crew}</strong>
            </div>

            <div>
              <small>PROFILE</small>
              <strong>{mission.duration}</strong>
            </div>
          </div>
        </div>

        <div className="mission-phases">
          <span className="phase-heading">
            FLIGHT SEQUENCE
          </span>

          {mission.phases.map(
            (phase, index) => (
              <div
                className="phase"
                key={phase}
              >
                <span>
                  {String(index + 1).padStart(
                    2,
                    "0"
                  )}
                </span>

                <i />

                <strong>{phase}</strong>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
