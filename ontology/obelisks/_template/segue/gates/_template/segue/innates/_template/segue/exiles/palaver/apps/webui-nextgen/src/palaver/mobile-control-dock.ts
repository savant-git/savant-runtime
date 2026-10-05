import {
  useWorkspaceStore
} from "./state/workspace-store"


type Cleanup = () => void


const modules = [
  {
    id: "chat",
    label: "chat"
  },
  {
    id: "terminal",
    label: "terminal"
  },
  {
    id: "memory",
    label: "memory"
  },
  {
    id: "uploads",
    label: "uploads"
  },
  {
    id: "search",
    label: "search"
  },
  {
    id: "source",
    label: "files"
  }
] as const


export function installMobileControlDock(): Cleanup {
  const existing =
    document.getElementById(
      "palaver-mobile-control-dock"
    )

  if (existing) {
    existing.remove()
  }


  const dock =
    document.createElement(
      "nav"
    )

  dock.id =
    "palaver-mobile-control-dock"

  dock.setAttribute(
    "aria-label",
    "palaver mobile navigation"
  )


  Object.assign(
    dock.style,
    {
      position: "fixed",
      left: "8px",
      right: "8px",
      bottom: "30px",
      zIndex: "2147483647",
      display: "flex",
      gap: "5px",
      padding: "7px",
      overflowX: "auto",
      background:
        "rgba(3,4,7,.96)",
      border:
        "1px solid rgba(255,255,255,.16)",
      borderRadius:
        "14px",
      boxShadow:
        "0 12px 50px rgba(0,0,0,.6)",
      pointerEvents:
        "auto",
      touchAction:
        "manipulation",
      WebkitOverflowScrolling:
        "touch"
    }
  )


  const activate = (
    id: typeof modules[number]["id"]
  ) => {
    useWorkspaceStore
      .getState()
      .setActive(
        id
      )
  }


  for (const module of modules) {
    const button =
      document.createElement(
        "button"
      )

    button.type =
      "button"

    button.textContent =
      module.label

    button.dataset.palaverModule =
      module.id


    Object.assign(
      button.style,
      {
        flex: "0 0 auto",
        minWidth: "72px",
        minHeight: "44px",
        padding: "0 10px",
        border:
          "1px solid rgba(255,255,255,.14)",
        borderRadius:
          "10px",
        background:
          "rgba(255,255,255,.05)",
        color:
          "#ece8dc",
        font:
          "600 11px system-ui, sans-serif",
        letterSpacing:
          ".06em",
        textTransform:
          "uppercase",
        pointerEvents:
          "auto",
        touchAction:
          "manipulation"
      }
    )


    let activatedAt = 0


    const run = (
      event: Event
    ) => {
      event.stopPropagation()

      const now =
        performance.now()

      if (
        now - activatedAt
        < 350
      ) {
        return
      }

      activatedAt =
        now

      activate(
        module.id
      )
    }


    button.addEventListener(
      "touchstart",
      run,
      {
        passive: true
      }
    )

    button.addEventListener(
      "pointerdown",
      run
    )

    button.addEventListener(
      "click",
      run
    )


    dock.appendChild(
      button
    )
  }


  document.body.appendChild(
    dock
  )


  return () => {
    dock.remove()
  }
}
