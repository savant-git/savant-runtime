"use strict";

(() => {
  const canvas = document.getElementById("atlas-canvas");
  const ctx = canvas.getContext("2d", { alpha: false });

  const minimap = document.getElementById("atlas-minimap");
  const mini = minimap.getContext("2d", { alpha: false });

  const inspector = document.getElementById("atlas-inspector");
  const inspectorTitle = document.getElementById("atlas-inspector-title");
  const inspectorBody = document.getElementById("atlas-inspector-body");

  const searchPanel = document.getElementById("atlas-search");
  const searchInput = document.getElementById("atlas-search-input");
  const searchResults = document.getElementById("atlas-search-results");

  const healthLabel = document.getElementById("atlas-health");
  const zoomLabel = document.getElementById("atlas-zoom-label");
  const selectionLabel = document.getElementById("atlas-selection-label");
  const metricsLabel = document.getElementById("atlas-metrics");
  const semantic = document.getElementById("atlas-semantic");
  const toast = document.getElementById("atlas-toast");

  const state = {
    projection: null,
    nodes: [],
    edges: [],
    nodeById: new Map(),
    childrenById: new Map(),
    parentById: new Map(),
    taskDependencies: new Map(),
    taskDependents: new Map(),
    layout: new Map(),
    regions: [],
    spatial: new Map(),
    cellSize: 110,
    selectedId: null,
    searchMatches: [],
    searchIndex: -1,
    lens: "all",
    dependencyTrace: false,
    unresolvedOnly: false,
    view: {
      x: 0,
      y: 0,
      scale: 1,
    },
    pointer: {
      active: false,
      moved: false,
      id: null,
      x: 0,
      y: 0,
      startX: 0,
      startY: 0,
      startViewX: 0,
      startViewY: 0,
    },
    touches: new Map(),
    pinchDistance: null,
    pinchScale: null,
    world: {
      x: 0,
      y: 0,
      width: 1000,
      height: 1000,
    },
    frameRequested: false,
  };

  const regionPalette = [
    "#4d6b75",
    "#6b5a78",
    "#596f5e",
    "#79644e",
    "#475f7c",
    "#75545d",
    "#5d6650",
    "#4f6c69",
    "#706454",
    "#625879",
    "#536474",
    "#72605c",
  ];

  function requestFrame() {
    if (state.frameRequested) {
      return;
    }

    state.frameRequested = true;

    requestAnimationFrame(() => {
      state.frameRequested = false;
      draw();
    });
  }

  function resizeCanvasElement(element, context) {
    const rect = element.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));

    if (element.width !== width || element.height !== height) {
      element.width = width;
      element.height = height;
    }

    context.setTransform(dpr, 0, 0, dpr, 0, 0);

    return {
      width: rect.width,
      height: rect.height,
      dpr,
    };
  }

  function hashText(text) {
    let hash = 2166136261;

    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }

    return hash >>> 0;
  }

  function nodeColor(node) {
    if (!node) {
      return "#778388";
    }

    if (node.kind === "task") {
      if (node.placement === "unresolved") {
        return "#a06063";
      }

      return "#b0a05f";
    }

    if (node.authority_class === "authority-bearing") {
      return "#9c6f78";
    }

    if (node.authority_class === "authority-adjacent") {
      return "#826c87";
    }

    if (node.authority_class === "runtime-state") {
      return "#617a87";
    }

    if (node.authority_class === "assurance") {
      return "#6d7d5c";
    }

    return "#56666d";
  }

  function regionColor(region) {
    return regionPalette[
      hashText(region) % regionPalette.length
    ];
  }

  function worldToScreen(x, y) {
    return {
      x: x * state.view.scale + state.view.x,
      y: y * state.view.scale + state.view.y,
    };
  }

  function screenToWorld(x, y) {
    return {
      x: (x - state.view.x) / state.view.scale,
      y: (y - state.view.y) / state.view.scale,
    };
  }

  function normalizeGraph() {
    state.nodes = Array.isArray(state.projection?.nodes)
      ? state.projection.nodes
      : [];

    state.edges = Array.isArray(state.projection?.edges)
      ? state.projection.edges
      : [];

    state.nodeById.clear();
    state.childrenById.clear();
    state.parentById.clear();
    state.taskDependencies.clear();
    state.taskDependents.clear();

    for (const node of state.nodes) {
      state.nodeById.set(node.id, node);
    }

    for (const edge of state.edges) {
      if (edge.kind === "contains") {
        if (!state.childrenById.has(edge.source)) {
          state.childrenById.set(edge.source, []);
        }

        state.childrenById.get(edge.source).push(edge.target);
        state.parentById.set(edge.target, edge.source);
      }

      if (edge.kind === "task-dependency") {
        if (!state.taskDependencies.has(edge.source)) {
          state.taskDependencies.set(edge.source, new Set());
        }

        if (!state.taskDependents.has(edge.target)) {
          state.taskDependents.set(edge.target, new Set());
        }

        state.taskDependencies.get(edge.source).add(edge.target);
        state.taskDependents.get(edge.target).add(edge.source);
      }
    }

    for (const children of state.childrenById.values()) {
      children.sort();
    }
  }

  function groupByRegion() {
    const groups = new Map();

    for (const node of state.nodes) {
      if (node.kind === "task") {
        continue;
      }

      const region = node.region || "unclassified";

      if (!groups.has(region)) {
        groups.set(region, []);
      }

      groups.get(region).push(node);
    }

    const taskNodes = state.nodes.filter((node) => node.kind === "task");

    return {
      groups,
      taskNodes,
    };
  }

  function partitionHorizontal(items, x, y, width, height) {
    const total = items.reduce(
      (sum, item) => sum + item.weight,
      0
    ) || 1;

    let cursor = x;

    return items.map((item, index) => {
      const remaining = x + width - cursor;

      const itemWidth = index === items.length - 1
        ? remaining
        : width * (item.weight / total);

      const rect = {
        x: cursor,
        y,
        width: Math.max(1, itemWidth),
        height,
      };

      cursor += itemWidth;

      return {
        ...item,
        rect,
      };
    });
  }

  function partitionVertical(items, x, y, width, height) {
    const total = items.reduce(
      (sum, item) => sum + item.weight,
      0
    ) || 1;

    let cursor = y;

    return items.map((item, index) => {
      const remaining = y + height - cursor;

      const itemHeight = index === items.length - 1
        ? remaining
        : height * (item.weight / total);

      const rect = {
        x,
        y: cursor,
        width,
        height: Math.max(1, itemHeight),
      };

      cursor += itemHeight;

      return {
        ...item,
        rect,
      };
    });
  }

  function computeTreemap(items, rect, depth = 0) {
    if (!items.length) {
      return [];
    }

    const normalized = items
      .slice()
      .sort((a, b) => {
        if (b.weight !== a.weight) {
          return b.weight - a.weight;
        }

        return String(a.key).localeCompare(String(b.key));
      });

    if (depth % 2 === 0) {
      return partitionHorizontal(
        normalized,
        rect.x,
        rect.y,
        rect.width,
        rect.height
      );
    }

    return partitionVertical(
      normalized,
      rect.x,
      rect.y,
      rect.width,
      rect.height
    );
  }

  function layoutRegionNodes(regionNodes, rect) {
    const rootCandidates = regionNodes.filter((node) => {
      const parentId = state.parentById.get(node.id);
      const parent = parentId ? state.nodeById.get(parentId) : null;

      return !parent || parent.region !== node.region;
    });

    const rootNodes = rootCandidates.length
      ? rootCandidates
      : regionNodes.slice(0, 1);

    const regionSet = new Set(regionNodes.map((node) => node.id));

    function subtreeWeight(nodeId) {
      let weight = 1;

      const children = state.childrenById.get(nodeId) || [];

      for (const childId of children) {
        if (regionSet.has(childId)) {
          weight += subtreeWeight(childId);
        }
      }

      return weight;
    }

    function recurse(nodeId, nodeRect, depth) {
      const node = state.nodeById.get(nodeId);

      if (!node) {
        return;
      }

      const padding = Math.max(
        3,
        Math.min(14, 10 - depth * 0.7)
      );

      const inner = {
        x: nodeRect.x + padding,
        y: nodeRect.y + padding,
        width: Math.max(4, nodeRect.width - padding * 2),
        height: Math.max(4, nodeRect.height - padding * 2),
      };

      state.layout.set(nodeId, {
        x: nodeRect.x,
        y: nodeRect.y,
        width: nodeRect.width,
        height: nodeRect.height,
        cx: nodeRect.x + nodeRect.width / 2,
        cy: nodeRect.y + nodeRect.height / 2,
        depth,
        region: node.region,
      });

      const children = (state.childrenById.get(nodeId) || [])
        .filter((childId) => regionSet.has(childId));

      if (!children.length) {
        return;
      }

      const items = children.map((childId) => ({
        key: childId,
        weight: subtreeWeight(childId),
      }));

      const partitions = computeTreemap(items, inner, depth + 1);

      for (const partition of partitions) {
        recurse(partition.key, partition.rect, depth + 1);
      }
    }

    const rootItems = rootNodes.map((node) => ({
      key: node.id,
      weight: subtreeWeight(node.id),
    }));

    const rootPartitions = computeTreemap(
      rootItems,
      rect,
      0
    );

    for (const partition of rootPartitions) {
      recurse(partition.key, partition.rect, 0);
    }
  }

  function layoutTasks(taskNodes) {
    const unresolved = [];

    for (const task of taskNodes) {
      const anchor = Array.isArray(task.anchors)
        ? task.anchors[0]
        : null;

      const anchorLayout = anchor
        ? state.layout.get(anchor.node_id)
        : null;

      if (!anchorLayout) {
        unresolved.push(task);
        continue;
      }

      const hash = hashText(task.id);

      const angle = ((hash % 360) * Math.PI) / 180;
      const radius = 8 + ((hash >>> 8) % 24);

      const x = anchorLayout.cx + Math.cos(angle) * radius;
      const y = anchorLayout.cy + Math.sin(angle) * radius;

      state.layout.set(task.id, {
        x: x - 4,
        y: y - 4,
        width: 8,
        height: 8,
        cx: x,
        cy: y,
        depth: anchorLayout.depth + 1,
        region: anchorLayout.region,
      });
    }

    const unresolvedRegion = state.regions.find(
      (region) => region.name === "unresolved-tasks"
    );

    if (!unresolvedRegion || !unresolved.length) {
      return;
    }

    const columns = Math.max(
      1,
      Math.ceil(Math.sqrt(unresolved.length))
    );

    const cellWidth = unresolvedRegion.rect.width / columns;
    const rows = Math.ceil(unresolved.length / columns);
    const cellHeight = unresolvedRegion.rect.height / Math.max(1, rows);

    unresolved
      .slice()
      .sort((a, b) => a.id.localeCompare(b.id))
      .forEach((task, index) => {
        const column = index % columns;
        const row = Math.floor(index / columns);

        const x = unresolvedRegion.rect.x
          + column * cellWidth
          + cellWidth / 2;

        const y = unresolvedRegion.rect.y
          + row * cellHeight
          + cellHeight / 2;

        state.layout.set(task.id, {
          x: x - 4,
          y: y - 4,
          width: 8,
          height: 8,
          cx: x,
          cy: y,
          depth: 0,
          region: "unresolved-tasks",
        });
      });
  }

  function computeLayout() {
    state.layout.clear();

    const { groups, taskNodes } = groupByRegion();

    const regionEntries = [...groups.entries()]
      .map(([name, nodes]) => ({
        name,
        nodes,
        weight: Math.max(1, nodes.length),
      }))
      .sort((a, b) => {
        if (b.weight !== a.weight) {
          return b.weight - a.weight;
        }

        return a.name.localeCompare(b.name);
      });

    if (taskNodes.some((node) => node.placement === "unresolved")) {
      regionEntries.push({
        name: "unresolved-tasks",
        nodes: [],
        weight: Math.max(
          8,
          taskNodes.filter((node) => node.placement === "unresolved").length
        ),
      });
    }

    const totalNodes = Math.max(1, state.nodes.length);
    const side = Math.max(1600, Math.sqrt(totalNodes) * 115);

    state.world = {
      x: 0,
      y: 0,
      width: side * 1.35,
      height: side,
    };

    const regionItems = regionEntries.map((entry) => ({
      key: entry.name,
      weight: entry.weight,
      entry,
    }));

    const regionPartitions = computeTreemap(
      regionItems,
      state.world,
      0
    );

    state.regions = regionPartitions.map((partition) => ({
      name: partition.key,
      rect: partition.rect,
      nodes: partition.entry.nodes,
      color: regionColor(partition.key),
    }));

    for (const region of state.regions) {
      const inset = 12;

      const rect = {
        x: region.rect.x + inset,
        y: region.rect.y + inset,
        width: Math.max(8, region.rect.width - inset * 2),
        height: Math.max(8, region.rect.height - inset * 2),
      };

      layoutRegionNodes(region.nodes, rect);
    }

    layoutTasks(taskNodes);
    rebuildSpatialIndex();
  }

  function spatialKey(x, y) {
    return [
      Math.floor(x / state.cellSize),
      Math.floor(y / state.cellSize),
    ].join(":");
  }

  function rebuildSpatialIndex() {
    state.spatial.clear();

    for (const [id, item] of state.layout.entries()) {
      const x1 = Math.floor(item.x / state.cellSize);
      const y1 = Math.floor(item.y / state.cellSize);
      const x2 = Math.floor((item.x + item.width) / state.cellSize);
      const y2 = Math.floor((item.y + item.height) / state.cellSize);

      for (let x = x1; x <= x2; x += 1) {
        for (let y = y1; y <= y2; y += 1) {
          const key = `${x}:${y}`;

          if (!state.spatial.has(key)) {
            state.spatial.set(key, []);
          }

          state.spatial.get(key).push(id);
        }
      }
    }
  }

  function visibleWorldBounds(size) {
    const topLeft = screenToWorld(0, 0);
    const bottomRight = screenToWorld(size.width, size.height);

    return {
      x1: Math.min(topLeft.x, bottomRight.x),
      y1: Math.min(topLeft.y, bottomRight.y),
      x2: Math.max(topLeft.x, bottomRight.x),
      y2: Math.max(topLeft.y, bottomRight.y),
    };
  }

  function rectIntersects(bounds, rect) {
    return !(
      rect.x + rect.width < bounds.x1
      || rect.x > bounds.x2
      || rect.y + rect.height < bounds.y1
      || rect.y > bounds.y2
    );
  }

  function semanticZoom() {
    const scale = state.view.scale;

    if (scale < 0.3) {
      return "world";
    }

    if (scale < 0.75) {
      return "district";
    }

    if (scale < 1.7) {
      return "locality";
    }

    return "task";
  }

  function nodeVisibleByLens(node) {
    if (state.unresolvedOnly) {
      return node.kind === "task" && node.placement === "unresolved";
    }

    if (state.lens === "tasks") {
      return node.kind === "task";
    }

    if (state.lens === "authority") {
      return node.authority_class === "authority-bearing"
        || node.authority_class === "authority-adjacent";
    }

    if (state.lens === "runtime") {
      return node.authority_class === "runtime-state";
    }

    return true;
  }

  function dependencySet() {
    if (!state.dependencyTrace || !state.selectedId) {
      return null;
    }

    const result = new Set([state.selectedId]);
    const queue = [state.selectedId];

    while (queue.length) {
      const current = queue.shift();

      const forward = state.taskDependencies.get(current) || [];
      const reverse = state.taskDependents.get(current) || [];

      for (const candidate of [...forward, ...reverse]) {
        if (!result.has(candidate)) {
          result.add(candidate);
          queue.push(candidate);
        }
      }
    }

    return result;
  }

  function drawRegion(region, bounds, zoom) {
    if (!rectIntersects(bounds, region.rect)) {
      return;
    }

    const topLeft = worldToScreen(region.rect.x, region.rect.y);
    const bottomRight = worldToScreen(
      region.rect.x + region.rect.width,
      region.rect.y + region.rect.height
    );

    const width = bottomRight.x - topLeft.x;
    const height = bottomRight.y - topLeft.y;

    ctx.fillStyle = region.color + "18";
    ctx.strokeStyle = region.color + "66";
    ctx.lineWidth = 1;

    ctx.fillRect(topLeft.x, topLeft.y, width, height);
    ctx.strokeRect(topLeft.x, topLeft.y, width, height);

    if (zoom === "world" || zoom === "district") {
      ctx.fillStyle = "#d9e0e2";
      ctx.font = zoom === "world"
        ? "600 13px ui-monospace, monospace"
        : "600 11px ui-monospace, monospace";

      ctx.fillText(
        region.name,
        topLeft.x + 8,
        topLeft.y + 17
      );
    }
  }

  function drawContainment(node, layout, zoom, traced) {
    if (!nodeVisibleByLens(node)) {
      return;
    }

    if (traced && !traced.has(node.id) && node.kind === "task") {
      return;
    }

    const topLeft = worldToScreen(layout.x, layout.y);
    const bottomRight = worldToScreen(
      layout.x + layout.width,
      layout.y + layout.height
    );

    const width = bottomRight.x - topLeft.x;
    const height = bottomRight.y - topLeft.y;

    const selected = node.id === state.selectedId;

    if (node.kind === "task") {
      const radius = selected ? 5.5 : 4;

      ctx.beginPath();
      ctx.arc(
        topLeft.x + width / 2,
        topLeft.y + height / 2,
        radius,
        0,
        Math.PI * 2
      );

      ctx.fillStyle = nodeColor(node);
      ctx.fill();

      if (selected) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      if (zoom === "task" || selected) {
        ctx.fillStyle = "#e5eaec";
        ctx.font = "10px ui-monospace, monospace";
        ctx.fillText(
          node.label || node.task_id || node.id,
          topLeft.x + radius + 5,
          topLeft.y + 3
        );
      }

      return;
    }

    if (zoom === "world") {
      return;
    }

    if (zoom === "district" && layout.depth > 1) {
      return;
    }

    if (zoom === "locality" && layout.depth > 4) {
      return;
    }

    ctx.fillStyle = nodeColor(node) + (
      selected ? "70" : "22"
    );

    ctx.strokeStyle = selected
      ? "#ffffff"
      : nodeColor(node) + "66";

    ctx.lineWidth = selected ? 2 : 1;

    ctx.fillRect(topLeft.x, topLeft.y, width, height);

    if (width > 3 && height > 3) {
      ctx.strokeRect(topLeft.x, topLeft.y, width, height);
    }

    const labelThreshold = zoom === "district"
      ? 80
      : zoom === "locality"
        ? 50
        : 22;

    if (width > labelThreshold && height > 15) {
      ctx.fillStyle = "#bfc8cb";
      ctx.font = "9px ui-monospace, monospace";
      ctx.fillText(
        node.label || node.id,
        topLeft.x + 4,
        topLeft.y + 11,
        Math.max(0, width - 8)
      );
    }
  }

  function drawDependencyEdges(traced) {
    if (!state.dependencyTrace || !state.selectedId || !traced) {
      return;
    }

    ctx.save();
    ctx.strokeStyle = "rgba(228, 214, 155, 0.75)";
    ctx.lineWidth = 1.5;

    for (const edge of state.edges) {
      if (edge.kind !== "task-dependency") {
        continue;
      }

      if (!traced.has(edge.source) || !traced.has(edge.target)) {
        continue;
      }

      const source = state.layout.get(edge.source);
      const target = state.layout.get(edge.target);

      if (!source || !target) {
        continue;
      }

      const a = worldToScreen(source.cx, source.cy);
      const b = worldToScreen(target.cx, target.cy);

      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    ctx.restore();
  }

  function draw() {
    const size = resizeCanvasElement(canvas, ctx);

    ctx.fillStyle = "#050607";
    ctx.fillRect(0, 0, size.width, size.height);

    if (!state.projection) {
      ctx.fillStyle = "#89969b";
      ctx.font = "12px ui-monospace, monospace";
      ctx.fillText("loading atlas", 20, 30);
      return;
    }

    const bounds = visibleWorldBounds(size);
    const zoom = semanticZoom();
    const traced = dependencySet();

    zoomLabel.textContent = zoom;

    for (const region of state.regions) {
      drawRegion(region, bounds, zoom);
    }

    drawDependencyEdges(traced);

    const layouts = [...state.layout.entries()]
      .sort((a, b) => {
        const nodeA = state.nodeById.get(a[0]);
        const nodeB = state.nodeById.get(b[0]);

        const taskA = nodeA?.kind === "task" ? 1 : 0;
        const taskB = nodeB?.kind === "task" ? 1 : 0;

        if (taskA !== taskB) {
          return taskA - taskB;
        }

        return (a[1].depth || 0) - (b[1].depth || 0);
      });

    for (const [id, layout] of layouts) {
      const node = state.nodeById.get(id);

      if (!node) {
        continue;
      }

      if (!rectIntersects(bounds, layout)) {
        continue;
      }

      drawContainment(node, layout, zoom, traced);
    }

    drawMinimap(size);
    updateStatus();
  }

  function drawMinimap(mainSize) {
    const size = resizeCanvasElement(minimap, mini);

    mini.fillStyle = "#07090a";
    mini.fillRect(0, 0, size.width, size.height);

    const world = state.world;

    const scale = Math.min(
      size.width / world.width,
      size.height / world.height
    );

    const offsetX = (size.width - world.width * scale) / 2;
    const offsetY = (size.height - world.height * scale) / 2;

    for (const region of state.regions) {
      mini.fillStyle = region.color + "45";

      mini.fillRect(
        offsetX + region.rect.x * scale,
        offsetY + region.rect.y * scale,
        region.rect.width * scale,
        region.rect.height * scale
      );
    }

    const topLeft = screenToWorld(0, 0);
    const bottomRight = screenToWorld(mainSize.width, mainSize.height);

    mini.strokeStyle = "#ffffff";
    mini.lineWidth = 1;

    mini.strokeRect(
      offsetX + topLeft.x * scale,
      offsetY + topLeft.y * scale,
      (bottomRight.x - topLeft.x) * scale,
      (bottomRight.y - topLeft.y) * scale
    );
  }

  function fitWorld() {
    const rect = canvas.getBoundingClientRect();

    const padding = 30;

    const scale = Math.min(
      (rect.width - padding * 2) / state.world.width,
      (rect.height - padding * 2) / state.world.height
    );

    state.view.scale = Math.max(0.02, scale);
    state.view.x = padding;
    state.view.y = padding;

    requestFrame();
  }

  function resetView() {
    state.view = {
      x: 0,
      y: 0,
      scale: 1,
    };

    fitWorld();
  }

  function focusNode(id, desiredScale = null) {
    const layout = state.layout.get(id);

    if (!layout) {
      return;
    }

    const rect = canvas.getBoundingClientRect();

    const scale = desiredScale || Math.max(
      state.view.scale,
      1.5
    );

    state.view.scale = Math.min(6, Math.max(0.03, scale));

    state.view.x = rect.width / 2 - layout.cx * state.view.scale;
    state.view.y = rect.height / 2 - layout.cy * state.view.scale;

    selectNode(id);
    requestFrame();
  }

  function hitTest(screenX, screenY) {
    const world = screenToWorld(screenX, screenY);
    const cell = state.spatial.get(spatialKey(world.x, world.y)) || [];

    const candidates = cell
      .map((id) => {
        const layout = state.layout.get(id);
        const node = state.nodeById.get(id);

        return {
          id,
          layout,
          node,
        };
      })
      .filter(({ layout, node }) => {
        if (!layout || !node || !nodeVisibleByLens(node)) {
          return false;
        }

        const tolerance = node.kind === "task"
          ? 8 / state.view.scale
          : 0;

        return world.x >= layout.x - tolerance
          && world.x <= layout.x + layout.width + tolerance
          && world.y >= layout.y - tolerance
          && world.y <= layout.y + layout.height + tolerance;
      })
      .sort((a, b) => {
        const taskA = a.node.kind === "task" ? 1 : 0;
        const taskB = b.node.kind === "task" ? 1 : 0;

        if (taskA !== taskB) {
          return taskB - taskA;
        }

        return (b.layout.depth || 0) - (a.layout.depth || 0);
      });

    return candidates[0]?.id || null;
  }

  function escaped(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function chips(values) {
    if (!values?.length) {
      return "<span class=\"atlas-chip\">none</span>";
    }

    return `
      <div class="atlas-chip-list">
        ${values.map((value) => (
          `<span class="atlas-chip">${escaped(value)}</span>`
        )).join("")}
      </div>
    `;
  }

  function field(name, value) {
    if (
      value === undefined
      || value === null
      || value === ""
    ) {
      return "";
    }

    return `
      <dl class="atlas-field">
        <dt>${escaped(name)}</dt>
        <dd>${value}</dd>
      </dl>
    `;
  }

  function breadcrumb(node) {
    const parts = [];
    let current = node;

    while (current) {
      parts.push(current.label || current.id);

      const parentId = state.parentById.get(current.id);
      current = parentId
        ? state.nodeById.get(parentId)
        : null;
    }

    return parts.reverse();
  }

  function renderInspector(node) {
    inspectorTitle.textContent = node.label || node.task_id || node.id;

    const anchors = Array.isArray(node.anchors)
      ? node.anchors.map((anchor) => (
          `${anchor.method}: ${anchor.resolved_path || anchor.requested_path}`
        ))
      : [];

    const dependencies = Array.isArray(node.dependencies)
      ? node.dependencies
      : [];

    const sources = Array.isArray(node.sources)
      ? node.sources.map((source) => (
          `${source.source} ${source.source_pointer}`
        ))
      : [];

    inspectorBody.innerHTML = [
      field("kind", escaped(node.kind)),
      field("id", escaped(node.id)),
      field("task id", escaped(node.task_id)),
      field("status", escaped(node.status)),
      field("owner", escaped(node.owner)),
      field("path", escaped(node.path)),
      field("relative path", escaped(node.relative_path)),
      field("region", escaped(node.region)),
      field("authority", escaped(node.authority_class)),
      field("placement", escaped(node.placement)),
      field("breadcrumb", chips(breadcrumb(node))),
      field("anchors", chips(anchors)),
      field("dependencies", chips(dependencies)),
      field("sources", chips(sources)),
      node.kind === "task"
        ? field(
            "why here",
            escaped(
              node.placement === "unresolved"
                ? "no explicit deterministic runtime path was available"
                : "task projected onto explicit runtime path substance"
            )
          )
        : "",
    ].join("");

    inspector.hidden = false;
  }

  function selectNode(id) {
    state.selectedId = id;

    const node = id
      ? state.nodeById.get(id)
      : null;

    if (!node) {
      selectionLabel.textContent = "nothing selected";
      inspector.hidden = true;
      semantic.textContent = "nothing selected";
      history.replaceState(null, "", location.pathname);
      requestFrame();
      return;
    }

    selectionLabel.textContent = node.label || node.id;
    semantic.textContent = `selected ${node.label || node.id}`;

    renderInspector(node);

    const hash = `#node=${encodeURIComponent(id)}`;

    if (location.hash !== hash) {
      history.replaceState(null, "", hash);
    }

    requestFrame();
  }

  function updateStatus() {
    const metrics = state.projection?.metrics || {};

    metricsLabel.textContent = [
      `${metrics.node_count ?? state.nodes.length} nodes`,
      `${metrics.task_count ?? 0} tasks`,
      `${metrics.unresolved_task_count ?? 0} unresolved`,
    ].join(" · ");
  }

  function showToast(message) {
    toast.textContent = message;
    toast.hidden = false;

    clearTimeout(showToast.timer);

    showToast.timer = setTimeout(() => {
      toast.hidden = true;
    }, 1800);
  }

  function searchText(node) {
    return [
      node.id,
      node.label,
      node.path,
      node.relative_path,
      node.task_id,
      node.owner,
      node.status,
      node.region,
      node.authority_class,
      ...(node.dependencies || []),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
  }

  function performSearch(query) {
    const normalized = query.trim().toLowerCase();

    if (!normalized) {
      state.searchMatches = [];
      state.searchIndex = -1;
      searchResults.innerHTML = "";
      return;
    }

    const tokens = normalized.split(/\s+/).filter(Boolean);

    const matches = state.nodes
      .map((node) => {
        const text = searchText(node);

        let score = 0;

        for (const token of tokens) {
          if (!text.includes(token)) {
            return null;
          }

          if ((node.label || "").toLowerCase().startsWith(token)) {
            score += 10;
          } else if ((node.task_id || "").toLowerCase().includes(token)) {
            score += 6;
          } else if ((node.path || "").toLowerCase().includes(token)) {
            score += 4;
          } else {
            score += 1;
          }
        }

        return {
          node,
          score,
        };
      })
      .filter(Boolean)
      .sort((a, b) => {
        if (b.score !== a.score) {
          return b.score - a.score;
        }

        return String(a.node.label || a.node.id)
          .localeCompare(String(b.node.label || b.node.id));
      })
      .slice(0, 100);

    state.searchMatches = matches;
    state.searchIndex = matches.length ? 0 : -1;

    searchResults.innerHTML = matches
      .map(({ node }, index) => `
        <button
          type="button"
          class="atlas-search-result"
          role="option"
          data-search-index="${index}"
          aria-selected="${index === 0 ? "true" : "false"}"
        >
          <strong>${escaped(node.label || node.task_id || node.id)}</strong>
          <small>${escaped(node.path || node.task_id || node.id)}</small>
        </button>
      `)
      .join("");
  }

  function updateSearchSelection() {
    const buttons = searchResults.querySelectorAll(".atlas-search-result");

    buttons.forEach((button, index) => {
      button.setAttribute(
        "aria-selected",
        index === state.searchIndex ? "true" : "false"
      );
    });

    const current = buttons[state.searchIndex];

    current?.scrollIntoView({
      block: "nearest",
    });
  }

  function openSearch() {
    searchPanel.hidden = false;
    searchInput.focus();
    searchInput.select();
  }

  function closeSearch() {
    searchPanel.hidden = true;
    searchInput.value = "";
    performSearch("");
    canvas.focus?.();
  }

  function applyLens(lens) {
    state.lens = state.lens === lens
      ? "all"
      : lens;

    state.unresolvedOnly = false;

    document.querySelectorAll("[data-action]").forEach((button) => {
      const action = button.dataset.action;

      button.dataset.active = (
        action === state.lens
        || (action === "dependencies" && state.dependencyTrace)
        || (action === "unresolved" && state.unresolvedOnly)
      )
        ? "true"
        : "false";
    });

    requestFrame();
  }

  function toggleUnresolved() {
    state.unresolvedOnly = !state.unresolvedOnly;

    if (state.unresolvedOnly) {
      state.lens = "all";
    }

    document.querySelector('[data-action="unresolved"]').dataset.active =
      state.unresolvedOnly ? "true" : "false";

    requestFrame();
  }

  function toggleDependencies() {
    state.dependencyTrace = !state.dependencyTrace;

    document.querySelector('[data-action="dependencies"]').dataset.active =
      state.dependencyTrace ? "true" : "false";

    requestFrame();
  }

  async function loadProjection() {
    healthLabel.textContent = "loading";

    const response = await fetch("/api/atlas", {
      cache: "no-store",
      credentials: "same-origin",
    });

    if (!response.ok) {
      throw new Error(`atlas api returned ${response.status}`);
    }

    const projection = await response.json();

    if (
      projection?.projection_only !== true
      || projection?.mutation_authority !== false
    ) {
      throw new Error("atlas authority boundary rejected");
    }

    state.projection = projection;

    normalizeGraph();
    computeLayout();
    fitWorld();

    healthLabel.textContent = "live";

    const hashMatch = location.hash.match(/^#node=(.+)$/);

    if (hashMatch) {
      const id = decodeURIComponent(hashMatch[1]);

      if (state.nodeById.has(id)) {
        focusNode(id, 1.7);
      }
    }

    requestFrame();
  }

  function zoomAt(screenX, screenY, factor) {
    const before = screenToWorld(screenX, screenY);

    state.view.scale = Math.min(
      8,
      Math.max(
        0.02,
        state.view.scale * factor
      )
    );

    state.view.x = screenX - before.x * state.view.scale;
    state.view.y = screenY - before.y * state.view.scale;

    requestFrame();
  }

  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();

    const rect = canvas.getBoundingClientRect();

    zoomAt(
      event.clientX - rect.left,
      event.clientY - rect.top,
      Math.exp(-event.deltaY * 0.0014)
    );
  }, { passive: false });

  canvas.addEventListener("pointerdown", (event) => {
    canvas.setPointerCapture(event.pointerId);

    state.pointer.active = true;
    state.pointer.moved = false;
    state.pointer.id = event.pointerId;
    state.pointer.x = event.clientX;
    state.pointer.y = event.clientY;
    state.pointer.startX = event.clientX;
    state.pointer.startY = event.clientY;
    state.pointer.startViewX = state.view.x;
    state.pointer.startViewY = state.view.y;

    canvas.dataset.dragging = "true";

    state.touches.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    });

    if (state.touches.size === 2) {
      const points = [...state.touches.values()];
      state.pinchDistance = Math.hypot(
        points[1].x - points[0].x,
        points[1].y - points[0].y
      );
      state.pinchScale = state.view.scale;
    }
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!state.pointer.active && !state.touches.has(event.pointerId)) {
      return;
    }

    if (state.touches.has(event.pointerId)) {
      state.touches.set(event.pointerId, {
        x: event.clientX,
        y: event.clientY,
      });
    }

    if (state.touches.size === 2) {
      const points = [...state.touches.values()];

      const distance = Math.hypot(
        points[1].x - points[0].x,
        points[1].y - points[0].y
      );

      const centerX = (points[0].x + points[1].x) / 2;
      const centerY = (points[0].y + points[1].y) / 2;

      const rect = canvas.getBoundingClientRect();

      const factor = state.pinchDistance
        ? distance / state.pinchDistance
        : 1;

      const targetScale = Math.min(
        8,
        Math.max(
          0.02,
          (state.pinchScale || state.view.scale) * factor
        )
      );

      const world = screenToWorld(
        centerX - rect.left,
        centerY - rect.top
      );

      state.view.scale = targetScale;
      state.view.x = centerX - rect.left - world.x * targetScale;
      state.view.y = centerY - rect.top - world.y * targetScale;

      requestFrame();
      return;
    }

    if (event.pointerId !== state.pointer.id) {
      return;
    }

    const dx = event.clientX - state.pointer.startX;
    const dy = event.clientY - state.pointer.startY;

    if (Math.abs(dx) + Math.abs(dy) > 4) {
      state.pointer.moved = true;
    }

    state.view.x = state.pointer.startViewX + dx;
    state.view.y = state.pointer.startViewY + dy;

    requestFrame();
  });

  function finishPointer(event) {
    state.touches.delete(event.pointerId);

    if (state.touches.size < 2) {
      state.pinchDistance = null;
      state.pinchScale = null;
    }

    if (event.pointerId !== state.pointer.id) {
      return;
    }

    const rect = canvas.getBoundingClientRect();

    if (!state.pointer.moved) {
      const id = hitTest(
        event.clientX - rect.left,
        event.clientY - rect.top
      );

      selectNode(id);
    }

    state.pointer.active = false;
    state.pointer.id = null;
    canvas.dataset.dragging = "false";
  }

  canvas.addEventListener("pointerup", finishPointer);
  canvas.addEventListener("pointercancel", finishPointer);

  canvas.addEventListener("dblclick", (event) => {
    const rect = canvas.getBoundingClientRect();

    const id = hitTest(
      event.clientX - rect.left,
      event.clientY - rect.top
    );

    if (id) {
      focusNode(id, Math.max(2, state.view.scale * 1.45));
    } else {
      zoomAt(
        event.clientX - rect.left,
        event.clientY - rect.top,
        1.5
      );
    }
  });

  minimap.addEventListener("click", (event) => {
    const rect = minimap.getBoundingClientRect();

    const world = state.world;

    const scale = Math.min(
      rect.width / world.width,
      rect.height / world.height
    );

    const offsetX = (rect.width - world.width * scale) / 2;
    const offsetY = (rect.height - world.height * scale) / 2;

    const worldX = (event.clientX - rect.left - offsetX) / scale;
    const worldY = (event.clientY - rect.top - offsetY) / scale;

    const main = canvas.getBoundingClientRect();

    state.view.x = main.width / 2 - worldX * state.view.scale;
    state.view.y = main.height / 2 - worldY * state.view.scale;

    requestFrame();
  });

  searchInput.addEventListener("input", () => {
    performSearch(searchInput.value);
  });

  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();

      if (state.searchMatches.length) {
        state.searchIndex = Math.min(
          state.searchMatches.length - 1,
          state.searchIndex + 1
        );

        updateSearchSelection();
      }
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();

      if (state.searchMatches.length) {
        state.searchIndex = Math.max(
          0,
          state.searchIndex - 1
        );

        updateSearchSelection();
      }
    }

    if (event.key === "Enter") {
      event.preventDefault();

      const match = state.searchMatches[state.searchIndex];

      if (match) {
        closeSearch();
        focusNode(match.node.id, 1.8);
      }
    }

    if (event.key === "Escape") {
      event.preventDefault();
      closeSearch();
    }
  });

  searchResults.addEventListener("click", (event) => {
    const button = event.target.closest("[data-search-index]");

    if (!button) {
      return;
    }

    const index = Number(button.dataset.searchIndex);
    const match = state.searchMatches[index];

    if (match) {
      closeSearch();
      focusNode(match.node.id, 1.8);
    }
  });

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");

    if (!button) {
      return;
    }

    const action = button.dataset.action;

    if (action === "fit") {
      fitWorld();
    }

    if (action === "reset") {
      resetView();
    }

    if (action === "authority") {
      applyLens("authority");
    }

    if (action === "tasks") {
      applyLens("tasks");
    }

    if (action === "dependencies") {
      toggleDependencies();
    }

    if (action === "unresolved") {
      toggleUnresolved();
    }

    if (action === "search") {
      openSearch();
    }

    if (action === "close-search") {
      closeSearch();
    }

    if (action === "close-inspector") {
      selectNode(null);
    }

    if (action === "refresh") {
      try {
        await loadProjection();
        showToast("atlas refreshed");
      } catch (error) {
        showToast(error.message);
      }
    }
  });

  document.addEventListener("keydown", (event) => {
    if (
      event.target instanceof HTMLInputElement
      || event.target instanceof HTMLTextAreaElement
    ) {
      return;
    }

    if (
      event.key === "/"
      || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k")
    ) {
      event.preventDefault();
      openSearch();
      return;
    }

    if (event.key.toLowerCase() === "f") {
      fitWorld();
      return;
    }

    if (event.key === "0") {
      resetView();
      return;
    }

    if (event.key.toLowerCase() === "t") {
      applyLens("tasks");
      return;
    }

    if (event.key.toLowerCase() === "a") {
      applyLens("authority");
      return;
    }

    if (event.key.toLowerCase() === "d") {
      toggleDependencies();
      return;
    }

    if (event.key === "Escape") {
      if (!searchPanel.hidden) {
        closeSearch();
      } else if (!inspector.hidden) {
        selectNode(null);
      }
    }
  });

  window.addEventListener("resize", requestFrame);

  window.addEventListener("hashchange", () => {
    const match = location.hash.match(/^#node=(.+)$/);

    if (!match) {
      return;
    }

    const id = decodeURIComponent(match[1]);

    if (state.nodeById.has(id)) {
      focusNode(id);
    }
  });

  loadProjection()
    .catch((error) => {
      healthLabel.textContent = "failed";
      semantic.textContent = error.message;

      ctx.fillStyle = "#050607";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      showToast(error.message);
    });
})();
