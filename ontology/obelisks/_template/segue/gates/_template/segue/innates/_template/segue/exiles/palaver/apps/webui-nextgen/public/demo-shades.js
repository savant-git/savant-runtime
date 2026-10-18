
"use strict";

(function (global) {
  const framework = global.SavantDemoFramework;

  if (!framework) {
    throw new Error(
      "demo-shades requires demo-framework.js"
    );
  }

  function node(tag, className, content) {
    const result = document.createElement(tag);

    if (className) {
      result.className = className;
    }

    if (content !== undefined) {
      result.textContent = String(content);
    }

    return result;
  }

  function panel(title, description) {
    const result = node(
      "article",
      "savant-demo__panel"
    );

    if (title) {
      result.append(
        node("h3", "", title)
      );
    }

    if (description) {
      result.append(
        node("p", "", description)
      );
    }

    return result;
  }

  framework.registerShade({
    id: "overview",

    render({ options }) {
      const container = node(
        "div",
        "savant-demo__grid"
      );

      for (const item of options.items || []) {
        const section = panel(
          item.title,
          item.description
        );

        if (item.value !== undefined) {
          section.append(
            node(
              "div",
              "savant-demo__value",
              item.value
            )
          );
        }

        container.append(section);
      }

      return container;
    }
  });

  framework.registerShade({
    id: "metrics",

    render({ options }) {
      const container = node(
        "div",
        "savant-demo__grid"
      );

      for (const metric of options.metrics || []) {
        const section = panel();

        section.append(
          node(
            "div",
            "savant-demo__label",
            metric.label
          ),
          node(
            "div",
            "savant-demo__value",
            metric.value
          )
        );

        if (metric.description) {
          section.append(
            node(
              "p",
              "",
              metric.description
            )
          );
        }

        container.append(section);
      }

      return container;
    }
  });

  framework.registerShade({
    id: "comparison",

    render({ options }) {
      const container = node(
        "div",
        "savant-demo__grid"
      );

      for (const candidate of options.candidates || []) {
        const section = panel(
          candidate.title,
          candidate.description
        );

        for (const metric of candidate.metrics || []) {
          const line = node(
            "div",
            "savant-demo__metric"
          );

          line.append(
            node(
              "span",
              "savant-demo__label",
              metric.label
            ),
            node(
              "strong",
              "",
              metric.value
            )
          );

          section.append(line);
        }

        container.append(section);
      }

      return container;
    }
  });

  framework.registerShade({
    id: "timeline",

    render({ options }) {
      const container = node(
        "div",
        "savant-demo__timeline"
      );

      for (const event of options.events || []) {
        const section = panel(
          event.title,
          event.description
        );

        section.dataset.eventId = String(
          event.id || ""
        );

        if (event.status) {
          section.append(
            node(
              "span",
              "savant-demo__label",
              event.status
            )
          );
        }

        container.append(section);
      }

      return container;
    }
  });

  framework.registerShade({
    id: "composition",

    render({ options }) {
      const container = node(
        "div",
        "savant-demo__grid"
      );

      for (const component of options.components || []) {
        const section = panel(
          component.title,
          component.description
        );

        section.dataset.componentId = String(
          component.id || ""
        );

        if (component.role) {
          section.append(
            node(
              "div",
              "savant-demo__label",
              component.role
            )
          );
        }

        container.append(section);
      }

      return container;
    }
  });

  global.SavantDemoShades = Object.freeze({
    panel,
    node
  });
})(window);
