const state = {
  sourceRecords: [],
  projectedRecords: [],
  recipe: "chronology-explorer",
  query: "",
  kind: "",
  status: "",
  dense: false,
  selected: null,
  projection: null,
  bookmarks: new Set(
    JSON.parse(
      localStorage.getItem(
        "savant.coalesce.bookmarks"
      ) || "[]"
    )
  ),
};

const recipes = {
  "chronology-explorer":
    "Chronology Explorer",
  "evidence-atlas":
    "Evidence Atlas",
  "dependency-browser":
    "Dependency Browser",
  "decision-history":
    "Decision History",
  "system-health":
    "System Health",
  "authority-explorer":
    "Authority Explorer",
  "masterplan-viewer":
    "Masterplan Viewer",
  "provenance-explorer":
    "Provenance Explorer",
  "narrative-atlas":
    "Narrative Atlas",
};

const $ = (selector) =>
  document.querySelector(
    selector
  );

const recipeSelect =
  $("#recipe");

const queryInput =
  $("#query");

const kindFilter =
  $("#kind");

const statusFilter =
  $("#status");

const recordsElement =
  $("#records");

const summary =
  $("#summary");

const intel =
  $("#intel");

const currentGroup =
  $("#current-group");

const currentMeta =
  $("#current-meta");

const drawer =
  $("#drawer");

const drawerContent =
  $("#drawer-content");

const datasetFile =
  $("#dataset-file");


for (
  const [id, title]
  of Object.entries(recipes)
) {
  const option =
    document.createElement(
      "option"
    );

  option.value = id;
  option.textContent = title;

  recipeSelect.append(
    option
  );
}


function escapeHtml(value) {
  return String(
    value ?? ""
  )
    .replaceAll(
      "&",
      "&amp;"
    )
    .replaceAll(
      "<",
      "&lt;"
    )
    .replaceAll(
      ">",
      "&gt;"
    )
    .replaceAll(
      '"',
      "&quot;"
    );
}


function extractArray(data) {
  if (
    Array.isArray(data)
  ) {
    return data;
  }

  for (
    const key
    of [
      "records",
      "nodes",
      "items",
      "events",
      "entries",
    ]
  ) {
    if (
      Array.isArray(
        data?.[key]
      )
    ) {
      return data[key];
    }
  }

  return [];
}


function currentParameters() {
  const parameters = {
    query:
      state.query,
    lens_values: {},
  };

  if (state.kind) {
    parameters
      .lens_values
      .kind =
      state.kind;
  }

  if (state.status) {
    parameters
      .lens_values
      .status =
      state.status;
  }

  return parameters;
}


function currentRuntimeState() {
  return {
    bookmarks:
      [
        ...state.bookmarks,
      ],
  };
}


async function deriveProjection() {
  const response =
    await fetch(
      "/api/coalesce/project",
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body:
          JSON.stringify(
            {
              recipe:
                state.recipe,
              records:
                state.sourceRecords,
              state:
                currentRuntimeState(),
              parameters:
                currentParameters(),
            }
          ),
      }
    );

  const payload =
    await response.json();

  if (!response.ok) {
    throw new Error(
      payload.error
      || (
        "Coalesce projection "
        + "failed"
      )
    );
  }

  state.projection =
    payload;

  state.projectedRecords =
    payload
      ?.interface
      ?.records
    ?? payload.records
    ?? [];

  rebuildFilters();

  render();
}


function requestProjection() {
  deriveProjection()
    .catch(
      (error) => {
        recordsElement.innerHTML = `
          <div class="empty">
            ${escapeHtml(
              error.message
            )}
          </div>
        `;
      }
    );
}


function groupKey(record) {
  if (
    state.recipe
    === "dependency-browser"
  ) {
    return (
      record.category
      || "general"
    );
  }

  if (
    state.recipe
    === "system-health"
  ) {
    return (
      record.status
      || "unknown"
    );
  }

  const date =
    String(
      record.date
      || ""
    );

  if (
    /^\d{4}/.test(
      date
    )
  ) {
    return date.slice(
      0,
      4
    );
  }

  return "Undated";
}


function renderCard(record) {
  return `
    <article
      class="card ${
        state.selected
        === record.id
        ? "selected"
        : ""
      }"
      data-id="${
        escapeHtml(
          record.id
        )
      }"
    >
      <div class="card-top">
        <div class="card-date">
          ${
            escapeHtml(
              record.date
              || "UNDATED"
            )
          }
        </div>

        <div>
          <div class="tags">
            <span class="tag">
              ${
                escapeHtml(
                  record.category
                  || "general"
                )
              }
            </span>

            <span class="tag">
              ${
                escapeHtml(
                  record.kind
                  || "record"
                )
              }
            </span>

            <span class="tag">
              ${
                escapeHtml(
                  record.status
                  || "unknown"
                )
              }
            </span>
          </div>

          <h2>
            ${
              escapeHtml(
                record.title
                || record.id
              )
            }
          </h2>

          <div class="preview">
            ${
              escapeHtml(
                record.preview
                || ""
              )
            }
          </div>
        </div>

        <button
          class="expand"
          aria-label="Expand"
        >+</button>
      </div>

      <div class="card-detail">
${
  escapeHtml(
    record.body
    || record.preview
    || ""
  )
}

ID: ${
  escapeHtml(
    record.id
  )
}
Relationships: ${
  Array.isArray(
    record.relationships
  )
  ? record.relationships.length
  : 0
}
      </div>
    </article>
  `;
}


function render() {
  const groups =
    new Map();

  for (
    const record
    of state.projectedRecords
  ) {
    const key =
      groupKey(record);

    if (!groups.has(key)) {
      groups.set(
        key,
        []
      );
    }

    groups
      .get(key)
      .push(record);
  }

  const execution =
    state.projection
      ?.interface
      ?.summary
    ?? {};

  summary.innerHTML = `
    <div class="metric">
      <b>${
        state.sourceRecords.length
      }</b>
      <span>source records</span>
    </div>

    <div class="metric">
      <b>${
        state.projectedRecords.length
      }</b>
      <span>projected records</span>
    </div>

    <div class="metric">
      <b>${
        execution
          .executed_piece_count
        ?? 0
      }</b>
      <span>executed pieces</span>
    </div>
  `;

  if (
    !state.projectedRecords.length
  ) {
    recordsElement.innerHTML = `
      <div class="empty">
        Load a neutral JSON dataset.
      </div>
    `;

    currentGroup.textContent =
      "—";

    currentMeta.textContent =
      "";

    return;
  }

  recordsElement.innerHTML =
    [
      ...groups.entries(),
    ]
      .map(
        ([key, rows]) => `
          <section
            class="group"
            data-group="${
              escapeHtml(key)
            }"
          >
            <h2 class="group-title">
              ${
                escapeHtml(key)
              }
            </h2>

            ${
              rows
                .map(
                  renderCard
                )
                .join("")
            }
          </section>
        `
      )
      .join("");

  const first =
    [
      ...groups.keys(),
    ][0];

  currentGroup.textContent =
    first;

  currentMeta.textContent =
    `${
      groups.get(first).length
    } records`;
}


function rebuildFilters() {
  const kinds =
    [
      ...new Set(
        state.projectedRecords
          .map(
            (record) =>
              record.kind
          )
          .filter(Boolean)
      ),
    ].sort();

  const statuses =
    [
      ...new Set(
        state.projectedRecords
          .map(
            (record) =>
              record.status
          )
          .filter(Boolean)
      ),
    ].sort();

  const existingKind =
    state.kind;

  const existingStatus =
    state.status;

  kindFilter.innerHTML =
    (
      '<option value="">'
      + "All kinds"
      + "</option>"
    );

  statusFilter.innerHTML =
    (
      '<option value="">'
      + "All statuses"
      + "</option>"
    );

  for (
    const value
    of kinds
  ) {
    const option =
      document.createElement(
        "option"
      );

    option.value = value;
    option.textContent =
      value;

    kindFilter.append(
      option
    );
  }

  for (
    const value
    of statuses
  ) {
    const option =
      document.createElement(
        "option"
      );

    option.value = value;
    option.textContent =
      value;

    statusFilter.append(
      option
    );
  }

  kindFilter.value =
    existingKind;

  statusFilter.value =
    existingStatus;
}


function loadDataset(data) {
  state.sourceRecords =
    extractArray(data);

  state.selected =
    null;

  intel.innerHTML =
    "";

  requestProjection();
}


function findRecord(id) {
  return (
    state.projectedRecords
      .find(
        (record) =>
          String(record.id)
          === String(id)
      )
    || null
  );
}


function selectRecord(id) {
  state.selected = id;

  const record =
    findRecord(id);

  if (!record) {
    return;
  }

  intel.innerHTML = `
    <strong>
      ${
        escapeHtml(
          record.title
          || record.id
        )
      }
    </strong>

    <p>
      ${
        escapeHtml(
          record.preview
          || ""
        )
      }
    </p>

    <p>
      ${
        escapeHtml(
          record.kind
          || "record"
        )
      }
      /
      ${
        escapeHtml(
          record.status
          || "unknown"
        )
      }
    </p>

    <button
      id="open-selected"
    >
      Open details
    </button>

    <button
      id="bookmark-selected"
    >
      ${
        state.bookmarks.has(
          record.id
        )
        ? "Unbookmark"
        : "Bookmark"
      }
    </button>
  `;

  $("#open-selected")
    ?.addEventListener(
      "click",
      () =>
        openDrawer(
          record
        )
    );

  $("#bookmark-selected")
    ?.addEventListener(
      "click",
      () =>
        toggleBookmark(
          record
        )
    );

  render();
}


function toggleBookmark(record) {
  if (
    state.bookmarks.has(
      record.id
    )
  ) {
    state.bookmarks.delete(
      record.id
    );
  } else {
    state.bookmarks.add(
      record.id
    );
  }

  localStorage.setItem(
    "savant.coalesce.bookmarks",
    JSON.stringify(
      [
        ...state.bookmarks,
      ]
    )
  );

  selectRecord(
    record.id
  );
}


function openDrawer(record) {
  drawerContent.innerHTML = `
    <h2>
      ${
        escapeHtml(
          record.title
          || record.id
        )
      }
    </h2>

    <p>
      ${
        escapeHtml(
          record.date
          || "Undated"
        )
      }
    </p>

    <pre>${
      escapeHtml(
        record.body
        || record.preview
        || ""
      )
    }</pre>

    <hr>

    <pre>${
      escapeHtml(
        JSON.stringify(
          {
            id:
              record.id,
            kind:
              record.kind,
            status:
              record.status,
            category:
              record.category,
            provenance:
              record.provenance,
            relationships:
              record.relationships,
          },
          null,
          2
        )
      )
    }</pre>
  `;

  drawer.classList.add(
    "open"
  );

  drawer.setAttribute(
    "aria-hidden",
    "false"
  );
}


recordsElement
  .addEventListener(
    "click",
    (event) => {
      const card =
        event.target.closest(
          ".card"
        );

      if (!card) {
        return;
      }

      selectRecord(
        card.dataset.id
      );

      if (
        event.target.closest(
          ".expand"
        )
      ) {
        card.classList.toggle(
          "open"
        );
      }
    }
  );


queryInput
  .addEventListener(
    "input",
    () => {
      state.query =
        queryInput.value;

      requestProjection();
    }
  );


kindFilter
  .addEventListener(
    "change",
    () => {
      state.kind =
        kindFilter.value;

      requestProjection();
    }
  );


statusFilter
  .addEventListener(
    "change",
    () => {
      state.status =
        statusFilter.value;

      requestProjection();
    }
  );


recipeSelect
  .addEventListener(
    "change",
    () => {
      state.recipe =
        recipeSelect.value;

      $("#title").textContent =
        recipes[
          state.recipe
        ];

      requestProjection();
    }
  );


$("#density")
  .addEventListener(
    "click",
    () => {
      state.dense =
        !state.dense;

      document.body
        .classList
        .toggle(
          "dense",
          state.dense
        );
    }
  );


$("#focus-search")
  .addEventListener(
    "click",
    () =>
      queryInput.focus()
  );


$("#dataset-load")
  .addEventListener(
    "click",
    () =>
      datasetFile.click()
  );


datasetFile
  .addEventListener(
    "change",
    async () => {
      const file =
        datasetFile
          .files?.[0];

      if (!file) {
        return;
      }

      const text =
        await file.text();

      loadDataset(
        JSON.parse(text)
      );
    }
  );


$("#drawer-close")
  .addEventListener(
    "click",
    () => {
      drawer.classList.remove(
        "open"
      );

      drawer.setAttribute(
        "aria-hidden",
        "true"
      );
    }
  );


$("#export")
  .addEventListener(
    "click",
    () => {
      const payload = {
        schema:
          "savant://coalesce/export/1",
        recipe:
          state.recipe,
        projection:
          state.projection,
        bookmarks:
          [
            ...state.bookmarks,
          ],
      };

      const blob =
        new Blob(
          [
            JSON.stringify(
              payload,
              null,
              2
            ),
          ],
          {
            type:
              "application/json",
          }
        );

      const url =
        URL.createObjectURL(
          blob
        );

      const anchor =
        document.createElement(
          "a"
        );

      anchor.href =
        url;

      anchor.download =
        `${
          state.recipe
        }.json`;

      anchor.click();

      setTimeout(
        () =>
          URL.revokeObjectURL(
            url
          ),
        1000
      );
    }
  );


document
  .addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "/"
        && document.activeElement
        !== queryInput
      ) {
        event.preventDefault();

        queryInput.focus();
      }

      if (
        event.key
        === "Escape"
      ) {
        drawer.classList.remove(
          "open"
        );

        queryInput.blur();
      }

      if (
        event.key
          .toLowerCase()
        === "d"
      ) {
        state.dense =
          !state.dense;

        document.body
          .classList
          .toggle(
            "dense",
            state.dense
          );
      }
    }
  );


loadDataset([]);
