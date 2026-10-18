
"use strict";

(function (global) {
  const framework = global.SavantDemoFramework;

  if (!framework) {
    throw new Error(
      "demo-urge-definition requires demo-framework.js"
    );
  }

  const definition = framework.registerDemo({
    id: "urge",

    title: "urge",

    subtitle: "iterative intelligence",

    description:
      "Explore objective-driven iterative improvement.",

    status: "illustrative",

    initialView: "overview",

    createState() {
      return {
        session: "ready",
        iteration: 0,
        selectedCandidate: null,
        history: []
      };
    },

    views: [
      {
        id: "overview",
        title: "Overview",
        description:
          "Explore the composition of iterative intelligence.",
        shade: "composition",
        options: {
          components: [
            {
              id: "urge",
              title: "urge",
              role: "iteration",
              description:
                "Owns the iterative improvement process."
            },
            {
              id: "opus",
              title: "opus",
              role: "provider orchestration",
              description:
                "Coordinates provider participation."
            },
            {
              id: "underscore",
              title: "underscore",
              role: "structural discrimination",
              description:
                "Distinguishes structural alternatives."
            }
          ]
        }
      },
      {
        id: "session",
        title: "Session",
        description:
          "Inspect demonstration session state.",
        shade: "metrics",
        options: {
          metrics: [
            {
              label: "Execution",
              value: "Simulated",
              description:
                "This interface does not execute live inference."
            },
            {
              label: "Initial state",
              value: "Ready"
            }
          ]
        }
      },
      {
        id: "evolution",
        title: "Evolution",
        description:
          "Explore the sequence of evaluated changes.",
        shade: "timeline",
        options: {
          events: []
        }
      },
      {
        id: "comparison",
        title: "Comparison",
        description:
          "Compare candidate outcomes.",
        shade: "comparison",
        options: {
          candidates: []
        }
      },
      {
        id: "lineage",
        title: "Lineage",
        description:
          "Inspect the relationships between iterations.",
        shade: "timeline",
        options: {
          events: []
        }
      }
    ]
  });

  global.SavantUrgeDemoDefinition = definition;
})(window);
