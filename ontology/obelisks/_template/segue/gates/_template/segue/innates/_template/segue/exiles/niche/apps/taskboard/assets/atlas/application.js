import { createAtlasContext } from "./core.js?v=atlas-r13.4-entry-activation";
import { installComposition } from "./composition.js?v=atlas-r13.4-entry-activation";
import { installGeometry } from "./geometry.js?v=atlas-r13.4-entry-activation";
import { installShell } from "./shell.js?v=atlas-r13.4-entry-activation";
import { installRenderer } from "./renderer.js?v=atlas-r13.4-entry-activation";
import { installLifecycle } from "./lifecycle.js?v=atlas-r13.4-entry-activation";

export const build = "atlas-r13.4-entry-activation";

export function createAtlasApplication() {
  const ctx = createAtlasContext();
  installComposition(ctx);
  installGeometry(ctx);
  installShell(ctx);
  installRenderer(ctx);
  installLifecycle(ctx);

  const {state,dom,BUILD,emit,restore,ensureSurface,ensureNav,cache,defs,applyPrefs,bindControls,bindCore,resize,sync,open,select,fitWorld,fitTerritory,frontier,goBack,goForward,txt} = ctx;
  const install = () => {
    if (state.installed) return true;
    restore();
    ensureSurface();
    ensureNav();
    cache();
    if (!dom.surface || !dom.viewport || !dom.world) return false;
    defs();
    applyPrefs();
    bindControls();
    bindCore();
    resize();
    state.installed = true;
    document.documentElement.dataset.atlasBuild = build;
    sync();
    emit("installed", {build});
    return true;
  };

  const api = Object.freeze({
    open: () => { install(); return open(); },
    select: (id, options={}) => { install(); return select(txt(id), Boolean(options.focus), txt(options.source,"api")); },
    fit: () => { install(); return fitWorld(); },
    fitTerritory: id => { install(); return fitTerritory(txt(id)); },
    frontier: () => { install(); return frontier(); },
    back: () => { install(); return goBack(); },
    forward: () => { install(); return goForward(); },
    sync: () => { install(); return sync(); },
    dispose: () => ctx.dispose(),
    state: () => Object.freeze({
      build, legacyBuild: BUILD, architecture: "modular-instance-segue",
      installed: state.installed, active: state.active, ready: state.ready, selectedTaskId: state.selected,
      focusedTerritoryId: state.focusTerritory, semanticLevel: state.level, delimiter: state.semantic.delimiter,
      representedTaskCount: state.semantic.tasks.length, representedTerritoryCount: state.semantic.territories.length,
      lens: state.lens, priorityFilter: state.priority, forwardHistoryCount: state.forward.length, effectsMode: state.effects,
      recentLocations: Object.freeze(state.recent.slice()), viewport: Object.freeze({...state.viewport}), projectionGeneration: state.generation,
      mood: ctx.moods.current().name, modus: Object.freeze({...ctx.modus.forLevel(state.level)}),
      layoutLibrary: Object.freeze({name:"elkjs",version:"0.12.0",status:state.elkStatus,authorityEffect:"none"}),
      modules: Object.freeze(["core","composition","geometry","shell","renderer","lifecycle"]),
      authorityEffect:"none", projectionOnly:true
    })
  });

  return {ctx,api,install};
}
