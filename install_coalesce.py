#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

COALESCE = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "modus"
    / "segue"
    / "prodigals"
    / "coalesce"
)

OBJECT_DIRS = [
    "apps",
    "authority",
    "cache",
    "canon",
    "composition",
    "dynamic",
    "evolution",
    "evolution/migrations",
    "evolution/supersessions",
    "evolution/compatibility",
    "evolution/deprecations",
    "evolution/history",
    "facets",
    "graph",
    "graph/edges",
    "graph/nodes",
    "graph/projections",
    "graph/relationships",
    "interface",
    "interface/api",
    "interface/capabilities",
    "interface/contracts",
    "interface/events",
    "interface/runtime",
    "introspection",
    "lifecycle",
    "lifecycle/activate",
    "lifecycle/create",
    "lifecycle/destroy",
    "lifecycle/migrate",
    "lifecycle/recover",
    "lifecycle/suspend",
    "lineage",
    "metrics",
    "observatory",
    "observatory/diagnostics",
    "observatory/events",
    "observatory/logs",
    "observatory/metrics",
    "observatory/traces",
    "registry",
    "registry/capabilities",
    "registry/contracts",
    "registry/defaults",
    "registry/interfaces",
    "registry/manifests",
    "registry/schemas",
    "registry/templates",
    "registry/versions",
    "runtime",
    "runtime/api",
    "runtime/bootstrap",
    "runtime/bridge",
    "runtime/contracts",
    "runtime/events",
    "runtime/orchestration",
    "runtime/pipeline",
    "runtime/protocol",
    "runtime/providers",
    "runtime/services",
    "runtime/workers",
    "sessions",
    "state",
    "static",
    "static/public",
    "tests",
    "validation",
    "_template",
    "_template/segue",
    "moods",
]


SERVICE_PIECES: dict[str, list[str]] = {
    "temporal": [
        "date-normalizer",
        "temporal-index",
        "chronology-grouper",
        "density-map",
        "range-window",
        "temporal-zoom",
        "interval-resolver",
        "sequence-aligner",
        "temporal-conflict-detector",
    ],
    "record": [
        "record-model",
        "card-view",
        "detail-view",
        "provenance-view",
        "status-signals",
        "statistics",
        "record-normalizer",
        "record-comparator",
        "record-inspector",
    ],
    "discovery": [
        "exact-search",
        "fuzzy-search",
        "command-palette",
        "smart-query",
        "relevance-ranker",
        "result-highlighter",
        "facet-search",
        "query-history",
        "discovery-suggester",
    ],
    "lens": [
        "category-lens",
        "kind-lens",
        "status-lens",
        "conflict-lens",
        "bookmark-lens",
        "focus-lens",
        "provenance-lens",
        "relationship-lens",
        "confidence-lens",
    ],
    "gridd": [
        "gridd-builder",
        "relation-mapper",
        "pathfinder",
        "neighborhood-view",
        "gridd-view",
        "gridd-export",
        "centrality-analyzer",
        "cluster-view",
        "relationship-inspector",
    ],
    "workspace": [
        "compare",
        "notes",
        "bookmarks",
        "deep-links",
        "clipboard",
        "export-print",
        "workspace-history",
        "selection-set",
        "saved-view",
    ],
    "narrative": [
        "story-mode",
        "stepper",
        "spotlight",
        "milestones",
        "chapter-rail",
        "intel-panel",
        "branch-traversal",
        "narrative-path",
        "presentation-sequence",
    ],
    "shell": [
        "responsive-shell",
        "mobile-dock",
        "mobile-sheet",
        "keyboard-router",
        "view-modes",
        "accessibility",
        "command-router",
        "panel-manager",
        "layout-projector",
    ],
    "substrate": [
        "state-store",
        "persistence",
        "schema-guard",
        "plugin-sear",
        "dependency-loader",
        "recipe-compiler",
        "capability-negotiator",
        "composition-digest",
        "extension-host",
    ],
}


MOODS = [
    "anima",
    "weld",
    "kiln",
    "graft",
    "aria",
    "mantle",
    "fulcrum",
    "echelon",
    "ascent",
]


SERVICE_MOODS: dict[str, list[str]] = {
    "temporal": [
        "anima",
        "fulcrum",
        "echelon",
    ],
    "record": [
        "anima",
        "aria",
        "mantle",
    ],
    "discovery": [
        "aria",
        "graft",
        "ascent",
    ],
    "lens": [
        "graft",
        "mantle",
        "aria",
    ],
    "gridd": [
        "weld",
        "fulcrum",
        "ascent",
    ],
    "workspace": [
        "graft",
        "weld",
        "aria",
    ],
    "narrative": [
        "aria",
        "ascent",
        "echelon",
    ],
    "shell": [
        "aria",
        "fulcrum",
        "kiln",
    ],
    "substrate": [
        "kiln",
        "mantle",
        "weld",
    ],
}


RECIPES: dict[str, dict[str, Any]] = {
    "chronology-explorer": {
        "title": "Chronology Explorer",
        "services": [
            "temporal",
            "record",
            "discovery",
            "lens",
            "workspace",
            "narrative",
            "shell",
            "substrate",
        ],
    },
    "evidence-atlas": {
        "title": "Evidence Atlas",
        "services": [
            "temporal",
            "record",
            "discovery",
            "lens",
            "gridd",
            "workspace",
            "shell",
            "substrate",
        ],
    },
    "dependency-browser": {
        "title": "Dependency Browser",
        "services": [
            "record",
            "discovery",
            "lens",
            "gridd",
            "workspace",
            "shell",
            "substrate",
        ],
    },
    "decision-history": {
        "title": "Decision History",
        "services": [
            "temporal",
            "record",
            "discovery",
            "lens",
            "gridd",
            "workspace",
            "narrative",
            "shell",
            "substrate",
        ],
    },
    "system-health": {
        "title": "System Health",
        "services": [
            "record",
            "discovery",
            "lens",
            "gridd",
            "workspace",
            "shell",
            "substrate",
        ],
    },
    "authority-explorer": {
        "title": "Authority Explorer",
        "services": [
            "temporal",
            "record",
            "discovery",
            "lens",
            "gridd",
            "workspace",
            "narrative",
            "shell",
            "substrate",
        ],
    },
    "masterplan-viewer": {
        "title": "Masterplan Viewer",
        "services": [
            "temporal",
            "record",
            "discovery",
            "lens",
            "gridd",
            "workspace",
            "narrative",
            "shell",
            "substrate",
        ],
    },
    "provenance-explorer": {
        "title": "Provenance Explorer",
        "services": [
            "record",
            "discovery",
            "lens",
            "gridd",
            "workspace",
            "shell",
            "substrate",
        ],
    },
    "narrative-atlas": {
        "title": "Narrative Atlas",
        "services": [
            "temporal",
            "record",
            "discovery",
            "lens",
            "gridd",
            "workspace",
            "narrative",
            "shell",
            "substrate",
        ],
    },
}


DEPENDENCIES = [
    {
        "id": "js:fuse",
        "required": False,
        "purpose": "fuzzy-search acceleration",
        "fallback": "native relevance search",
        "attachment_mood": "graft",
    },
    {
        "id": "js:cytoscape",
        "required": False,
        "purpose": "interactive gridd projection",
        "fallback": "native relationship projection",
        "attachment_mood": "graft",
    },
    {
        "id": "js:vis-timeline",
        "required": False,
        "purpose": "interactive temporal projection",
        "fallback": "native chronology projection",
        "attachment_mood": "graft",
    },
]


ENHANCEMENTS = [
    "declarative application recipes",
    "ninefold service composition",
    "eighty-one reusable functional pieces",
    "governed composition cardinality",
    "canonical Mood bindings",
    "deterministic composition digest",
    "dataset-neutral ingestion",
    "schema-versioned records",
    "capability negotiation",
    "progressive dependency fallback",
    "optional gridd acceleration",
    "optional fuzzy-search acceleration",
    "adaptive record rendering",
    "search relevance scoring",
    "typed lenses",
    "conflict visualization",
    "provenance-aware records",
    "gridd path traversal",
    "serializable workspace state",
    "deep-linkable state",
    "local persistence",
    "responsive projection",
    "reduced-motion accessibility",
    "keyboard command routing",
    "extension attachment slots",
    "replayable composition manifests",
    "source-domain isolation",
]


RUNTIME = r'''#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parents[1]
REGISTRY = BASE / "registry"


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def valid_piece_count(count: int) -> bool:
    return (
        count == 3
        or (
            count > 0
            and count % 9 == 0
        )
    )


def compile_recipe(
    recipe_id: str,
) -> dict[str, Any]:
    piece_doc = load_json(
        REGISTRY / "pieces.json"
    )

    recipe_doc = load_json(
        REGISTRY / "recipes.json"
    )

    pieces = {
        item["id"]: item
        for item in piece_doc["pieces"]
    }

    recipes = {
        item["id"]: item
        for item in recipe_doc["recipes"]
    }

    if recipe_id not in recipes:
        raise KeyError(
            f"unknown Coalesce recipe: {recipe_id}"
        )

    recipe = recipes[recipe_id]

    selected = [
        pieces[piece_id]
        for piece_id
        in recipe["piece_ids"]
    ]

    selected.sort(
        key=lambda item: (
            item["service_ordinal"],
            item["piece_ordinal"],
        )
    )

    count = len(selected)

    if not valid_piece_count(count):
        raise RuntimeError(
            "Coalesce composition cardinality violation: "
            f"{count}"
        )

    compiled = {
        "id": (
            "projection:coalesce:"
            f"{recipe_id}"
        ),
        "kind": "application_projection",
        "owner": "prodigal:modus:coalesce",
        "recipe": recipe,
        "piece_count": count,
        "pieces": selected,
        "authority_effect": "none",
    }

    compiled["composition_digest"] = digest(
        compiled
    )

    return compiled


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="coalesce"
    )

    parser.add_argument(
        "operation",
        choices=[
            "list",
            "compile",
        ],
    )

    parser.add_argument(
        "recipe",
        nargs="?",
    )

    args = parser.parse_args()

    if args.operation == "list":
        print(
            json.dumps(
                load_json(
                    REGISTRY
                    / "recipes.json"
                ),
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    if not args.recipe:
        parser.error(
            "compile requires a recipe"
        )

    print(
        json.dumps(
            compile_recipe(
                args.recipe
            ),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
'''


TEST = r'''#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]


def main() -> int:
    pieces = json.loads(
        (
            BASE
            / "registry"
            / "pieces.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    recipes = json.loads(
        (
            BASE
            / "registry"
            / "recipes.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    moods = json.loads(
        (
            BASE
            / "moods"
            / "bindings.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert pieces["service_count"] == 9
    assert pieces["pieces_per_service"] == 9
    assert pieces["piece_count"] == 81
    assert len(pieces["pieces"]) == 81

    assert recipes["recipe_count"] == 9
    assert len(recipes["recipes"]) == 9

    assert moods["binding_count"] == 27

    for recipe in recipes["recipes"]:
        count = recipe["piece_count"]

        assert (
            count == 3
            or count % 9 == 0
        )

    result = subprocess.run(
        [
            "python3",
            str(
                BASE
                / "runtime"
                / "coalesce.py"
            ),
            "compile",
            "chronology-explorer",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    compiled = json.loads(
        result.stdout
    )

    assert compiled["piece_count"] % 9 == 0
    assert compiled["composition_digest"]
    assert compiled["owner"] == "prodigal:modus:coalesce"

    print("COALESCE: valid")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
'''


INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta
  name="viewport"
  content="width=device-width,initial-scale=1"
>
<title>Coalesce</title>
<link rel="stylesheet" href="./coalesce.css">
</head>
<body>
<header class="topbar">
  <div>
    <div class="eyebrow">SAVANT / MODUS / COALESCE</div>
    <h1 id="title">Coalesce</h1>
  </div>

  <div class="actions">
    <button id="focus-search">Search</button>
    <button id="density">Density</button>
    <button id="export">Export</button>
  </div>
</header>

<section class="toolbar">
  <select id="recipe"></select>

  <input
    id="query"
    type="search"
    placeholder="Search records"
  >

  <select id="kind">
    <option value="">All kinds</option>
  </select>

  <select id="status">
    <option value="">All statuses</option>
  </select>
</section>

<section
  id="summary"
  class="summary"
></section>

<main class="layout">
  <aside class="rail">
    <div class="sticky">
      <div class="label">Current group</div>
      <div id="current-group">—</div>
      <div id="current-meta"></div>
    </div>
  </aside>

  <section
    id="records"
    class="records"
  ></section>

  <aside class="intel">
    <div class="sticky">
      <div class="label">Selection</div>
      <div id="intel"></div>
    </div>
  </aside>
</main>

<div
  id="drawer"
  class="drawer"
  aria-hidden="true"
>
  <button
    id="drawer-close"
    aria-label="Close"
  >×</button>

  <div id="drawer-content"></div>
</div>

<input
  id="dataset-file"
  type="file"
  accept=".json,application/json"
  hidden
>

<button
  id="dataset-load"
  class="load"
>
  Load dataset
</button>

<script
  type="module"
  src="./coalesce.js"
></script>
</body>
</html>
'''


CSS = r''':root{
  color-scheme:dark;
  --bg:#0b0d0f;
  --panel:#14181b;
  --panel2:#191e22;
  --ink:#edf0f2;
  --muted:#89939b;
  --line:#293137;
  --accent:#e3c76f;
  --radius:14px;
}
*{box-sizing:border-box}
html{
  background:var(--bg);
  scroll-behavior:smooth
}
body{
  margin:0;
  background:
    radial-gradient(
      circle at 85% -15%,
      rgba(227,199,111,.08),
      transparent 36rem
    ),
    var(--bg);
  color:var(--ink);
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    sans-serif;
}
button,
input,
select{
  font:inherit;
  border:1px solid var(--line);
  background:var(--panel);
  color:var(--ink);
  border-radius:10px;
}
button{
  cursor:pointer;
  padding:9px 12px;
}
input,
select{
  padding:10px 12px;
}
.topbar{
  position:sticky;
  top:0;
  z-index:20;
  min-height:70px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:20px;
  padding:12px 22px;
  background:rgba(11,13,15,.88);
  backdrop-filter:blur(18px);
  border-bottom:1px solid var(--line);
}
.eyebrow,
.label{
  font:
    700 9px/1.2
    ui-monospace,
    monospace;
  letter-spacing:.14em;
  text-transform:uppercase;
  color:var(--muted);
}
h1{
  font-size:20px;
  margin:5px 0 0;
}
.actions{
  display:flex;
  gap:7px;
}
.toolbar{
  position:sticky;
  top:70px;
  z-index:19;
  display:grid;
  grid-template-columns:
    220px
    minmax(180px,1fr)
    160px
    160px;
  gap:8px;
  padding:10px 22px;
  background:rgba(11,13,15,.92);
  border-bottom:1px solid var(--line);
}
.summary{
  display:grid;
  grid-template-columns:
    repeat(3,minmax(0,1fr));
  gap:1px;
  background:var(--line);
  border-bottom:1px solid var(--line);
}
.metric{
  background:var(--panel);
  padding:14px 20px;
}
.metric b{
  display:block;
  font-size:22px;
}
.metric span{
  font-size:10px;
  color:var(--muted);
}
.layout{
  width:min(1500px,100%);
  margin:auto;
  display:grid;
  grid-template-columns:
    150px
    minmax(0,900px)
    minmax(220px,1fr);
  gap:36px;
  padding:44px 22px 110px;
}
.sticky{
  position:sticky;
  top:140px;
}
#current-group{
  font-size:42px;
  color:var(--accent);
  margin-top:10px;
}
#current-meta{
  font-size:11px;
  color:var(--muted);
}
.group{
  margin-bottom:50px;
}
.group-title{
  font-size:36px;
  margin:0 0 16px;
  letter-spacing:-.04em;
}
.card{
  margin-bottom:10px;
  border:1px solid var(--line);
  border-radius:var(--radius);
  background:
    linear-gradient(
      145deg,
      var(--panel2),
      var(--panel)
    );
  overflow:hidden;
}
.card-top{
  display:grid;
  grid-template-columns:
    92px
    minmax(0,1fr)
    auto;
  gap:12px;
  padding:14px;
  align-items:start;
}
.card-date{
  font:
    700 11px/1.4
    ui-monospace,
    monospace;
  color:var(--accent);
}
.tags{
  display:flex;
  gap:5px;
  flex-wrap:wrap;
  margin-bottom:6px;
}
.tag{
  border:1px solid #354047;
  border-radius:999px;
  padding:4px 6px;
  color:var(--muted);
  font:
    700 8px/1
    ui-monospace,
    monospace;
  text-transform:uppercase;
}
.card h2{
  font-size:17px;
  margin:0;
}
.preview{
  font-size:12px;
  color:#aab1b6;
  line-height:1.55;
  margin-top:6px;
}
.card-detail{
  display:none;
  border-top:1px solid var(--line);
  padding:14px;
  white-space:pre-wrap;
  font:
    12px/1.6
    ui-monospace,
    monospace;
}
.card.open .card-detail{
  display:block;
}
.card.selected{
  outline:1px solid var(--accent);
}
.intel{
  font-size:12px;
  color:#aab1b6;
}
.drawer{
  position:fixed;
  z-index:40;
  inset:0 0 0 auto;
  width:min(560px,100%);
  background:#101316;
  border-left:1px solid var(--line);
  padding:24px;
  transform:translateX(102%);
  transition:transform .28s ease;
  overflow:auto;
}
.drawer.open{
  transform:none;
}
#drawer-close{
  float:right;
  border:0;
  background:transparent;
  font-size:25px;
}
.load{
  position:fixed;
  right:18px;
  bottom:18px;
  z-index:30;
  border-radius:999px;
  box-shadow:
    0 14px 40px
    rgba(0,0,0,.36);
}
body.dense .preview{
  display:none;
}
body.dense .card-top{
  padding:9px 12px;
}
.empty{
  border:1px dashed var(--line);
  border-radius:var(--radius);
  padding:34px;
  color:var(--muted);
  text-align:center;
}
@media(max-width:950px){
  .layout{
    grid-template-columns:1fr;
  }
  .rail,
  .intel{
    display:none;
  }
  .toolbar{
    grid-template-columns:1fr 1fr;
  }
}
@media(max-width:600px){
  .topbar{
    padding:10px;
  }
  .toolbar{
    position:static;
    grid-template-columns:1fr;
    padding:8px 10px;
  }
  .summary{
    grid-template-columns:1fr;
  }
  .layout{
    padding:22px 8px 90px;
  }
  .card-top{
    grid-template-columns:
      70px
      minmax(0,1fr);
  }
  .card-top button{
    display:none;
  }
}
@media(prefers-reduced-motion:reduce){
  *{
    scroll-behavior:auto!important;
    transition:none!important;
  }
}
'''


JAVASCRIPT = r'''const state = {
  records: [],
  filtered: [],
  recipe: "chronology-explorer",
  query: "",
  kind: "",
  status: "",
  dense: false,
  selected: null,
  bookmarks: new Set(
    JSON.parse(
      localStorage.getItem(
        "savant.coalesce.bookmarks"
      ) || "[]"
    )
  ),
};

const recipes = {
  "chronology-explorer": "Chronology Explorer",
  "evidence-atlas": "Evidence Atlas",
  "dependency-browser": "Dependency Browser",
  "decision-history": "Decision History",
  "system-health": "System Health",
  "authority-explorer": "Authority Explorer",
  "masterplan-viewer": "Masterplan Viewer",
  "provenance-explorer": "Provenance Explorer",
  "narrative-atlas": "Narrative Atlas",
};

const $ = (selector) =>
  document.querySelector(selector);

const recipeSelect = $("#recipe");
const queryInput = $("#query");
const kindFilter = $("#kind");
const statusFilter = $("#status");
const recordsElement = $("#records");
const summary = $("#summary");
const intel = $("#intel");
const currentGroup = $("#current-group");
const currentMeta = $("#current-meta");
const drawer = $("#drawer");
const drawerContent = $("#drawer-content");
const datasetFile = $("#dataset-file");

for (
  const [id, title]
  of Object.entries(recipes)
) {
  const option =
    document.createElement("option");

  option.value = id;
  option.textContent = title;

  recipeSelect.append(option);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function normalizeRecord(
  input,
  index
) {
  const id = String(
    input.id
    ?? `record-${index}`
  );

  const date = String(
    input.date
    ?? input.occurred_at
    ?? input.created_at
    ?? input.timestamp
    ?? ""
  );

  const title = String(
    input.title
    ?? input.name
    ?? input.label
    ?? id
  );

  const preview = String(
    input.preview
    ?? input.description
    ?? input.summary
    ?? input.message
    ?? ""
  );

  const body = String(
    input.body
    ?? input.text
    ?? input.content
    ?? preview
  );

  const kind = String(
    input.kind
    ?? input.type
    ?? "record"
  );

  const status = String(
    input.status
    ?? "unknown"
  );

  const category = String(
    input.category
    ?? input.domain
    ?? input.owner
    ?? "general"
  );

  const relationships =
    input.relationships
    ?? input.links
    ?? input.dependencies
    ?? [];

  return {
    ...input,
    id,
    date,
    title,
    preview,
    body,
    kind,
    status,
    category,
    provenance:
      input.provenance
      ?? null,
    relationships:
      Array.isArray(relationships)
      ? relationships
      : [],
    _index: index,
  };
}

function relevance(
  record,
  terms
) {
  if (!terms.length) {
    return 1;
  }

  const title =
    record.title.toLowerCase();

  const category =
    record.category.toLowerCase();

  const kind =
    record.kind.toLowerCase();

  const status =
    record.status.toLowerCase();

  const haystack = [
    record.title,
    record.preview,
    record.body,
    record.kind,
    record.status,
    record.category,
  ]
    .join(" ")
    .toLowerCase();

  let score = 0;

  for (const term of terms) {
    if (title.includes(term)) {
      score += 9;
    }

    if (category.includes(term)) {
      score += 3;
    }

    if (kind.includes(term)) {
      score += 3;
    }

    if (status.includes(term)) {
      score += 3;
    }

    if (haystack.includes(term)) {
      score += 1;
    }
  }

  return score;
}

function groupKey(record) {
  if (
    state.recipe
    === "dependency-browser"
  ) {
    return record.category;
  }

  if (
    state.recipe
    === "system-health"
  ) {
    return record.status;
  }

  if (/^\d{4}/.test(record.date)) {
    return record.date.slice(0, 4);
  }

  return "Undated";
}

function applyFilters() {
  const terms = state.query
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);

  state.filtered = state.records
    .map((record) => ({
      record,
      relevance:
        relevance(
          record,
          terms
        ),
    }))
    .filter(
      ({
        record,
        relevance,
      }) => {
        if (
          terms.length
          && relevance === 0
        ) {
          return false;
        }

        if (
          state.kind
          && record.kind
          !== state.kind
        ) {
          return false;
        }

        if (
          state.status
          && record.status
          !== state.status
        ) {
          return false;
        }

        return true;
      }
    )
    .sort((left, right) => {
      const ld =
        left.record.date
        || "9999";

      const rd =
        right.record.date
        || "9999";

      if (ld !== rd) {
        return ld.localeCompare(rd);
      }

      return (
        right.relevance
        - left.relevance
      );
    });

  render();
}

function renderCard(
  record,
  score
) {
  return `
    <article
      class="card ${
        state.selected === record.id
        ? "selected"
        : ""
      }"
      data-id="${escapeHtml(record.id)}"
    >
      <div class="card-top">
        <div class="card-date">
          ${escapeHtml(
            record.date
            || "UNDATED"
          )}
        </div>

        <div>
          <div class="tags">
            <span class="tag">
              ${escapeHtml(record.category)}
            </span>

            <span class="tag">
              ${escapeHtml(record.kind)}
            </span>

            <span class="tag">
              ${escapeHtml(record.status)}
            </span>

            <span class="tag">
              REL ${score}
            </span>
          </div>

          <h2>
            ${escapeHtml(record.title)}
          </h2>

          <div class="preview">
            ${escapeHtml(record.preview)}
          </div>
        </div>

        <button
          class="expand"
          aria-label="Expand"
        >+</button>
      </div>

      <div class="card-detail">
${escapeHtml(record.body)}

ID: ${escapeHtml(record.id)}
Relationships: ${record.relationships.length}
      </div>
    </article>
  `;
}

function render() {
  const groups = new Map();

  for (
    const item
    of state.filtered
  ) {
    const key =
      groupKey(
        item.record
      );

    if (!groups.has(key)) {
      groups.set(
        key,
        []
      );
    }

    groups
      .get(key)
      .push(item);
  }

  summary.innerHTML = `
    <div class="metric">
      <b>${state.records.length}</b>
      <span>records</span>
    </div>

    <div class="metric">
      <b>${state.filtered.length}</b>
      <span>visible</span>
    </div>

    <div class="metric">
      <b>${groups.size}</b>
      <span>groups</span>
    </div>
  `;

  if (!state.filtered.length) {
    recordsElement.innerHTML = `
      <div class="empty">
        Load a neutral JSON dataset.
      </div>
    `;

    currentGroup.textContent = "—";
    currentMeta.textContent = "";

    return;
  }

  recordsElement.innerHTML = [
    ...groups.entries(),
  ]
    .map(
      ([key, rows]) => `
        <section
          class="group"
          data-group="${escapeHtml(key)}"
        >
          <h2 class="group-title">
            ${escapeHtml(key)}
          </h2>

          ${rows
            .map(
              ({
                record,
                relevance,
              }) =>
                renderCard(
                  record,
                  relevance
                )
            )
            .join("")}
        </section>
      `
    )
    .join("");

  const first =
    [...groups.keys()][0];

  currentGroup.textContent =
    first;

  currentMeta.textContent =
    `${groups.get(first).length} records`;
}

function rebuildFilters() {
  const kinds = [
    ...new Set(
      state.records.map(
        (record) =>
          record.kind
      )
    ),
  ].sort();

  const statuses = [
    ...new Set(
      state.records.map(
        (record) =>
          record.status
      )
    ),
  ].sort();

  kindFilter.innerHTML =
    '<option value="">All kinds</option>';

  statusFilter.innerHTML =
    '<option value="">All statuses</option>';

  for (const value of kinds) {
    const option =
      document.createElement(
        "option"
      );

    option.value = value;
    option.textContent = value;

    kindFilter.append(option);
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
    option.textContent = value;

    statusFilter.append(
      option
    );
  }
}

function extractArray(data) {
  if (Array.isArray(data)) {
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

function loadDataset(data) {
  const raw =
    extractArray(data);

  state.records =
    raw.map(
      normalizeRecord
    );

  rebuildFilters();
  applyFilters();
}

function selectRecord(id) {
  state.selected = id;

  const record =
    state.records.find(
      (candidate) =>
        candidate.id === id
    );

  if (!record) {
    return;
  }

  intel.innerHTML = `
    <strong>
      ${escapeHtml(record.title)}
    </strong>

    <p>
      ${escapeHtml(record.preview)}
    </p>

    <p>
      ${escapeHtml(record.kind)}
      /
      ${escapeHtml(record.status)}
    </p>

    <button id="open-selected">
      Open details
    </button>

    <button id="bookmark-selected">
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
        openDrawer(record)
    );

  $("#bookmark-selected")
    ?.addEventListener(
      "click",
      () =>
        toggleBookmark(record)
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
      [...state.bookmarks]
    )
  );

  render();
  selectRecord(record.id);
}

function openDrawer(record) {
  drawerContent.innerHTML = `
    <h2>
      ${escapeHtml(record.title)}
    </h2>

    <p>
      ${escapeHtml(
        record.date
        || "Undated"
      )}
    </p>

    <pre>
${escapeHtml(record.body)}
    </pre>

    <hr>

    <pre>
${escapeHtml(
  JSON.stringify(
    {
      id: record.id,
      kind: record.kind,
      status: record.status,
      category: record.category,
      provenance:
        record.provenance,
      relationships:
        record.relationships,
    },
    null,
    2
  )
)}
    </pre>
  `;

  drawer.classList.add(
    "open"
  );

  drawer.setAttribute(
    "aria-hidden",
    "false"
  );
}

recordsElement.addEventListener(
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

queryInput.addEventListener(
  "input",
  () => {
    state.query =
      queryInput.value;

    applyFilters();
  }
);

kindFilter.addEventListener(
  "change",
  () => {
    state.kind =
      kindFilter.value;

    applyFilters();
  }
);

statusFilter.addEventListener(
  "change",
  () => {
    state.status =
      statusFilter.value;

    applyFilters();
  }
);

recipeSelect.addEventListener(
  "change",
  () => {
    state.recipe =
      recipeSelect.value;

    $("#title").textContent =
      recipes[
        state.recipe
      ];

    applyFilters();
  }
);

$("#density").addEventListener(
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

datasetFile.addEventListener(
  "change",
  async () => {
    const file =
      datasetFile.files?.[0];

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
        records:
          state.filtered.map(
            (item) =>
              item.record
          ),
        bookmarks:
          [...state.bookmarks],
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

      anchor.href = url;
      anchor.download =
        `${state.recipe}.json`;

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

document.addEventListener(
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
'''


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_text(
    path: Path,
    value: str,
    *,
    executable: bool = False,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        value,
        encoding="utf-8",
    )

    if executable:
        path.chmod(0o755)


def valid_piece_count(
    count: int,
) -> bool:
    return (
        count == 3
        or (
            count > 0
            and count % 9 == 0
        )
    )


def build_pieces() -> dict[str, Any]:
    if len(SERVICE_PIECES) != 9:
        raise RuntimeError(
            "Coalesce requires exactly nine service families."
        )

    pieces: list[
        dict[str, Any]
    ] = []

    ordinal = 0

    for service_ordinal, (
        service,
        names,
    ) in enumerate(
        SERVICE_PIECES.items(),
        start=1,
    ):
        if len(names) != 9:
            raise RuntimeError(
                (
                    f"{service} must contain "
                    "exactly nine pieces."
                )
            )

        for piece_ordinal, name in enumerate(
            names,
            start=1,
        ):
            ordinal += 1

            pieces.append(
                {
                    "id": (
                        "slab:coalesce:"
                        f"{service}:{name}"
                    ),
                    "kind": "slab",
                    "canonical_name": name,
                    "owner": (
                        "prodigal:modus:"
                        "coalesce"
                    ),
                    "service": service,
                    "service_ordinal": (
                        service_ordinal
                    ),
                    "piece_ordinal": (
                        piece_ordinal
                    ),
                    "global_ordinal": (
                        ordinal
                    ),
                    "status": "active",
                    "shade": True,
                    "reusable": True,
                    "copy_on_compose": (
                        False
                    ),
                    "authority_effect": (
                        "none"
                    ),
                    "mood_bindings": [
                        (
                            "mood:"
                            f"{mood}"
                        )
                        for mood
                        in SERVICE_MOODS[
                            service
                        ]
                    ],
                    "slots": [
                        "renderer",
                        "data-source",
                        "policy",
                        "theme",
                        "transport",
                        "telemetry",
                        "extension",
                        "cert",
                        "linka",
                    ],
                }
            )

    if len(pieces) != 81:
        raise RuntimeError(
            "Coalesce requires exactly eighty-one pieces."
        )

    return {
        "id": "coalesce.pieces",
        "owner": (
            "prodigal:modus:coalesce"
        ),
        "kind": "piece_sear",
        "service_count": 9,
        "pieces_per_service": 9,
        "piece_count": 81,
        "pieces": pieces,
    }


def build_recipes(
    pieces_doc: dict[str, Any],
) -> dict[str, Any]:
    by_service: dict[
        str,
        list[str],
    ] = {}

    for piece in pieces_doc[
        "pieces"
    ]:
        by_service.setdefault(
            piece["service"],
            [],
        ).append(
            piece["id"]
        )

    recipes: list[
        dict[str, Any]
    ] = []

    for recipe_id, spec in (
        RECIPES.items()
    ):
        piece_ids: list[str] = []

        for service in spec[
            "services"
        ]:
            piece_ids.extend(
                by_service[
                    service
                ]
            )

        count = len(piece_ids)

        if not valid_piece_count(
            count
        ):
            raise RuntimeError(
                (
                    f"{recipe_id} has "
                    f"invalid piece count "
                    f"{count}"
                )
            )

        recipes.append(
            {
                "id": (
                    "application:"
                    f"coalesce:{recipe_id}"
                ),
                "recipe_id": (
                    recipe_id
                ),
                "title": (
                    spec["title"]
                ),
                "kind": (
                    "application"
                ),
                "owner": (
                    "prodigal:modus:"
                    "coalesce"
                ),
                "shade": True,
                "status": "active",
                "services": (
                    spec["services"]
                ),
                "piece_ids": (
                    piece_ids
                ),
                "piece_count": (
                    count
                ),
                "composition": (
                    "reference"
                ),
                "copy_substance": (
                    False
                ),
                "projection_owner": (
                    "filament"
                ),
                "visual_owner": (
                    "graffiti"
                ),
                "authority_effect": (
                    "none"
                ),
            }
        )

    if len(recipes) != 9:
        raise RuntimeError(
            "Coalesce requires exactly nine seed recipes."
        )

    return {
        "id": "coalesce.recipes",
        "owner": (
            "prodigal:modus:coalesce"
        ),
        "kind": "recipe_sear",
        "recipe_count": 9,
        "recipes": recipes,
    }


def build_moods() -> dict[str, Any]:
    bindings: list[
        dict[str, Any]
    ] = []

    for service, moods in (
        SERVICE_MOODS.items()
    ):
        if len(moods) != 3:
            raise RuntimeError(
                (
                    f"{service} must expose "
                    "exactly three Mood bindings."
                )
            )

        for mood in moods:
            if mood not in MOODS:
                raise RuntimeError(
                    f"Unknown Mood: {mood}"
                )

            bindings.append(
                {
                    "id": (
                        "mood-application:"
                        "coalesce:"
                        f"{service}:{mood}"
                    ),
                    "subject": (
                        "service:coalesce:"
                        f"{service}"
                    ),
                    "mood": (
                        f"mood:{mood}"
                    ),
                    "context": (
                        "composition"
                    ),
                    "authority_effect": (
                        "none"
                    ),
                    "parameters": {},
                    "lineage": {
                        "owner": (
                            "prodigal:"
                            "modus:coalesce"
                        )
                    },
                    "provenance": {
                        "basis": (
                            "Coalesce functional "
                            "composition"
                        )
                    },
                }
            )

    if len(bindings) != 27:
        raise RuntimeError(
            "Coalesce requires twenty-seven Mood bindings."
        )

    return {
        "id": (
            "coalesce.mood_bindings"
        ),
        "owner": (
            "prodigal:modus:coalesce"
        ),
        "binding_count": 27,
        "bindings": bindings,
    }


def build_entity() -> dict[str, Any]:
    return {
        "id": (
            "prodigal:modus:coalesce"
        ),
        "type": "prodigal",
        "status": "active",
        "parent": "exile:modus",
        "graph_address": (
            "ontology.exiles.modus."
            "prodigals.coalesce"
        ),
        "purpose": (
            "Compose reusable functional "
            "pieces into configurable "
            "application projections."
        ),
        "rule": (
            "Coalesce stores reusable pieces "
            "once and composes applications "
            "by reference."
        ),
        "numerical_canon": {
            "micro_composition": 3,
            "primary_modulus": 9,
            "service_count": 9,
            "pieces_per_service": 9,
            "piece_count": 81,
            "seed_recipe_count": 9,
        },
        "source_extraction": {
            "source_application": (
                "VISCERA_NEXUS_"
                "TIMELINE_APP_V5.html"
            ),
            "extraction_scope": (
                "functional patterns only"
            ),
            "source_domain": (
                "mayorgate"
            ),
            "source_domain_data_copied": (
                False
            ),
            "source_domain_status": (
                "excluded"
            ),
        },
        "attachments": [
            {
                "owner": "cataxis",
                "capability": (
                    "temporal semantics"
                ),
                "mode": "reference",
            },
            {
                "owner": "filament",
                "capability": (
                    "projection"
                ),
                "mode": "reference",
            },
            {
                "owner": "graffiti",
                "capability": (
                    "visual expression"
                ),
                "mode": "reference",
            },
            {
                "owner": "notary",
                "capability": (
                    "provenance"
                ),
                "mode": (
                    "optional-reference"
                ),
            },
            {
                "owner": "pact",
                "capability": (
                    "contracts"
                ),
                "mode": (
                    "optional-reference"
                ),
            },
            {
                "owner": "opus",
                "capability": (
                    "AI augmentation"
                ),
                "mode": (
                    "optional-reference"
                ),
            },
        ],
        "authority": str(
            COALESCE
            / "authority"
        ),
        "canon": str(
            COALESCE
            / "canon"
        ),
        "lineage": str(
            COALESCE
            / "lineage"
        ),
        "graph": str(
            COALESCE
            / "graph"
        ),
        "registry": str(
            COALESCE
            / "registry"
        ),
        "runtime": str(
            COALESCE
            / "runtime"
        ),
        "interface": str(
            COALESCE
            / "interface"
        ),
        "introspection": str(
            COALESCE
            / "introspection"
        ),
        "facets": str(
            COALESCE
            / "facets"
        ),
        "template": str(
            COALESCE
            / "_template"
        ),
    }


def main() -> int:
    COALESCE.mkdir(
        parents=True,
        exist_ok=True,
    )

    for relative in OBJECT_DIRS:
        (
            COALESCE
            / relative
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

    pieces = build_pieces()
    recipes = build_recipes(
        pieces
    )
    moods = build_moods()

    write_json(
        COALESCE
        / "entity.json",
        build_entity(),
    )

    write_json(
        COALESCE
        / "graph"
        / "node.json",
        {
            "id": (
                "prodigal:modus:"
                "coalesce"
            ),
            "label": "coalesce",
            "type": "prodigal",
            "parent": (
                "exile:modus"
            ),
            "parent_type": (
                "exile"
            ),
            "child_type": (
                "quirk"
            ),
            "graph_address": (
                "ontology.exiles.modus."
                "prodigals.coalesce"
            ),
        },
    )

    write_json(
        COALESCE
        / "lineage"
        / "lineage.json",
        {
            "id": (
                "coalesce.lineage"
            ),
            "owner": (
                "prodigal:modus:"
                "coalesce"
            ),
            "parents": [
                "exile:modus"
            ],
            "supersedes": [],
            "superseded_by": [],
            "source_extraction": (
                "functional-only"
            ),
        },
    )

    write_json(
        COALESCE
        / "registry"
        / "pieces.json",
        pieces,
    )

    write_json(
        COALESCE
        / "registry"
        / "recipes.json",
        recipes,
    )

    write_json(
        COALESCE
        / "registry"
        / "dependencies.json",
        {
            "id": (
                "coalesce.dependencies"
            ),
            "owner": (
                "prodigal:modus:"
                "coalesce"
            ),
            "dependency_count": 3,
            "dependencies": (
                DEPENDENCIES
            ),
        },
    )

    write_json(
        COALESCE
        / "registry"
        / "enhancements.json",
        {
            "id": (
                "coalesce.enhancements"
            ),
            "owner": (
                "prodigal:modus:"
                "coalesce"
            ),
            "enhancement_count": 27,
            "enhancements": (
                ENHANCEMENTS
            ),
        },
    )

    write_json(
        COALESCE
        / "registry"
        / "manifests"
        / "coalesce.json",
        {
            "id": (
                "manifest:coalesce"
            ),
            "owner": (
                "prodigal:modus:"
                "coalesce"
            ),
            "status": "active",
            "service_count": 9,
            "piece_count": 81,
            "recipe_count": 9,
            "mood_binding_count": 27,
            "authority_effect": (
                "none"
            ),
        },
    )

    write_json(
        COALESCE
        / "interface"
        / "capabilities"
        / "capabilities.json",
        {
            "id": (
                "coalesce.capabilities"
            ),
            "owner": (
                "prodigal:modus:"
                "coalesce"
            ),
            "type": (
                "capability_manifest"
            ),
            "status": "active",
            "capabilities": [
                "compose-application",
                "compile-recipe",
                "ingest-neutral-records",
                "project-chronology",
                "project-gridd",
                "search-records",
                "apply-lenses",
                "persist-workspace",
                "export-projection",
            ],
        },
    )

    write_json(
        COALESCE
        / "composition"
        / "imports.json",
        {
            "id": (
                "coalesce.imports"
            ),
            "owner": (
                "prodigal:modus:"
                "coalesce"
            ),
            "imports": [
                "exile:cataxis",
                "exile:filament",
                "exile:graffiti",
                "exile:notary",
                "exile:pact",
                "exile:opus",
            ],
        },
    )

    write_json(
        COALESCE
        / "composition"
        / "exports.json",
        {
            "id": (
                "coalesce.exports"
            ),
            "owner": (
                "prodigal:modus:"
                "coalesce"
            ),
            "exports": [
                "capability:compose-application",
                "capability:compile-recipe",
                "capability:project-application",
            ],
        },
    )

    write_json(
        COALESCE
        / "moods"
        / "bindings.json",
        moods,
    )

    write_json(
        COALESCE
        / "moods"
        / "available.json",
        {
            "id": (
                "coalesce.moods.available"
            ),
            "owner": (
                "prodigal:modus:"
                "coalesce"
            ),
            "moods": [
                f"mood:{mood}"
                for mood in MOODS
            ],
        },
    )

    write_json(
        COALESCE
        / "moods"
        / "active.json",
        {
            "id": (
                "coalesce.moods.active"
            ),
            "owner": (
                "prodigal:modus:"
                "coalesce"
            ),
            "bindings": [
                item["id"]
                for item
                in moods["bindings"]
            ],
        },
    )

    write_text(
        COALESCE
        / "runtime"
        / "__init__.py",
        "",
    )

    write_text(
        COALESCE
        / "runtime"
        / "coalesce.py",
        RUNTIME,
        executable=True,
    )

    write_text(
        COALESCE
        / "tests"
        / "test_coalesce.py",
        TEST,
        executable=True,
    )

    write_text(
        COALESCE
        / "static"
        / "public"
        / "index.html",
        INDEX_HTML,
    )

    write_text(
        COALESCE
        / "static"
        / "public"
        / "coalesce.css",
        CSS,
    )

    write_text(
        COALESCE
        / "static"
        / "public"
        / "coalesce.js",
        JAVASCRIPT,
    )

    write_text(
        COALESCE
        / "README.md",
        (
            "# Coalesce\n\n"
            "Modus-owned Prodigal for deterministic "
            "composition of reusable functional pieces "
            "into application projections.\n\n"
            "Coalesce contains no Mayorgate data.\n"
        ),
    )

    receipt = {
        "operation": (
            "install-coalesce"
        ),
        "passed": True,
        "path": str(
            COALESCE
        ),
        "owner": (
            "exile:modus"
        ),
        "identity": (
            "prodigal:modus:"
            "coalesce"
        ),
        "service_count": 9,
        "pieces_per_service": 9,
        "piece_count": 81,
        "recipe_count": 9,
        "mood_count": 9,
        "mood_binding_count": 27,
        "enhancement_count": 27,
        "optional_dependency_count": 3,
        "source_domain_data_copied": (
            False
        ),
        "piece_digest": (
            hashlib.sha256(
                json.dumps(
                    pieces,
                    sort_keys=True,
                ).encode(
                    "utf-8"
                )
            ).hexdigest()
        ),
    }

    write_json(
        COALESCE
        / "introspection"
        / "install_receipt.json",
        receipt,
    )

    print(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
