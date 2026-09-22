export function installComposition(ctx) {
  const {state, normalized, buildSemantic, recommendationId, coreProjection, taskId} = ctx;

  const segues = Object.freeze({
    projectionToSemantic(projection) {
      const normalizedProjection = normalized(projection);
      return Object.freeze({normalized: normalizedProjection, semantic: buildSemantic(normalizedProjection)});
    },
    taskToSpatial(taskOrId) {
      const id = typeof taskOrId === "string" ? taskOrId : taskId(taskOrId);
      const territoryId = state.semantic.taskToTerritory.get(id) ?? null;
      const taskGeometry = state.geometry.task.get(id) ?? null;
      const territoryGeometry = territoryId ? state.geometry.territory.get(territoryId) ?? null : null;
      return Object.freeze({id, territoryId, taskGeometry, territoryGeometry, authorityEffect:"none", projectionOnly:true});
    },
    recommendationToTask(projection = coreProjection()) {
      const id = recommendationId(projection);
      return id && state.semantic.taskById.has(id) ? id : null;
    },
    viewportToWorld(clientX, clientY, rect) {
      return Object.freeze({
        x: (clientX - rect.left - state.viewport.x) / state.viewport.scale,
        y: (clientY - rect.top - state.viewport.y) / state.viewport.scale
      });
    }
  });

  const modus = Object.freeze({
    forLevel(level) {
      return ctx.masks[level] ?? ctx.masks.world;
    },
    relationship(lens) {
      return Object.freeze({
        local: lens === "dependencies",
        aggregate: lens === "domains" || lens === "dependencies",
        heat: lens === "heatmap",
        authority: lens === "authority"
      });
    }
  });

  const moods = Object.freeze({
    current() {
      const mobile = state.size.w > 1 && state.size.w < 760;
      const degraded = !state.ready;
      const reduced = state.effects === "reduced" || Boolean(globalThis.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
      const focus = Boolean(state.selected || state.focusTerritory);
      return Object.freeze({mobile,degraded,reduced,focus,name:degraded?"degraded":mobile?"mobile":focus?"focused":reduced?"restrained":"default"});
    }
  });

  Object.assign(ctx,{segues,modus,moods});
  return ctx;
}
