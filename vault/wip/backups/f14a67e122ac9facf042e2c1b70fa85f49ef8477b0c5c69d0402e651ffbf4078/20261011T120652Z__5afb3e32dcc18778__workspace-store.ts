import {
  create
} from "zustand"

import {
  persist
} from "zustand/middleware"


export type PalaverModule =
  | "chat"
  | "terminal"
  | "memory"
  | "source"
  | "kindred"
  | "search"
  | "work"
  | "system"
  | "guide"


export type Observatory =
  PalaverModule


export type Density =
  | "compact"
  | "comfortable"
  | "expert"


export type WorkspaceMode =
  | "single"
  | "chat-terminal-split"


export type WorkspacePreset =
  | "conversation"
  | "inference"
  | "context"
  | "review"
  | "inspection"
  | "focus"


type TerminalStage = {
  id: number
  text: string
}


export type UploadedContext = {
  id: string
  name: string
  type: string
  size: number
  text: string
}


type State = {
  active:
    PalaverModule

  commandOpen:
    boolean

  focusMode:
    boolean

  density:
    Density

  workspaceMode:
    WorkspaceMode

  workspacePreset:
    WorkspacePreset

  leftPanelVisible:
    boolean

  rightPanelVisible:
    boolean

  statusbarVisible:
    boolean

  composerDraft:
    string

  terminalStage:
    TerminalStage | null

  lastActivity:
    string

  sourcePath:
    string

  uploadedContext:
    UploadedContext[]

  setActive: (
    value: PalaverModule
  ) => void

  setCommandOpen: (
    value: boolean
  ) => void

  toggleFocus:
    () => void

  cycleDensity:
    () => void

  setWorkspaceMode: (
    value: WorkspaceMode
  ) => void

  toggleChatTerminalSplit:
    () => void

  setWorkspacePreset: (
    value: WorkspacePreset
  ) => void

  applyWorkspacePreset: (
    value: WorkspacePreset
  ) => void

  toggleLeftPanel:
    () => void

  toggleRightPanel:
    () => void

  toggleStatusbar:
    () => void

  restoreWorkspace:
    () => void

  setComposerDraft: (
    value: string
  ) => void

  stageTerminal: (
    value: string
  ) => void

  clearTerminalStage:
    () => void

  setLastActivity: (
    value: string
  ) => void

  openSource: (
    path: string
  ) => void

  addUploadedContext: (
    value: UploadedContext[]
  ) => void

  removeUploadedContext: (
    id: string
  ) => void

  clearUploadedContext:
    () => void
}


function presetState(
  value: WorkspacePreset
) {
  switch (
    value
  ) {
    case "conversation":
      return {
        active:
          "chat" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "inference":
      return {
        active:
          "system" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "context":
      return {
        active:
          "memory" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "review":
      return {
        active:
          "source" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "inspection":
      return {
        active:
          "kindred" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "focus":
      return {
        active:
          "chat" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          true,

        leftPanelVisible:
          false,

        rightPanelVisible:
          false,

        statusbarVisible:
          true
      }
  }
}


export const useWorkspaceStore =
  create<State>()(
    persist(
      (
        set,
        get
      ) => ({
        active:
          "chat",

        commandOpen:
          false,

        focusMode:
          false,

        density:
          "comfortable",

        workspaceMode:
          "single",

        workspacePreset:
          "conversation",

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true,

        composerDraft:
          "",

        terminalStage:
          null,

        lastActivity:
          "palaver ready",

        sourcePath:
          "",

        uploadedContext:
          [],

        setActive:
          active =>
            set({
              active,

              workspaceMode:
                "single",

              lastActivity:
                `opened ${active}`
            }),

        setCommandOpen:
          commandOpen =>
            set({
              commandOpen
            }),

        toggleFocus:
          () => {
            const enabled =
              !get().focusMode

            set({
              focusMode:
                enabled,

              lastActivity:
                enabled
                  ? "focus mode enabled"
                  : "focus mode disabled"
            })
          },

        cycleDensity:
          () => {
            const current =
              get().density

            const density:
              Density =
                current
                === "comfortable"
                  ? "compact"
                  : current
                  === "compact"
                    ? "expert"
                    : "comfortable"

            set({
              density,

              lastActivity:
                `density ${density}`
            })
          },

        setWorkspaceMode:
          workspaceMode =>
            set({
              workspaceMode
            }),

        toggleChatTerminalSplit:
          () => {
            const opening =
              get().workspaceMode
              !== "chat-terminal-split"

            set({
              workspaceMode:
                opening
                  ? "chat-terminal-split"
                  : "single",

              lastActivity:
                opening
                  ? (
                    "chat and terminal "
                    + "split opened"
                  )
                  : (
                    "chat and terminal "
                    + "split closed"
                  )
            })
          },

        setWorkspacePreset:
          workspacePreset =>
            set({
              workspacePreset
            }),

        applyWorkspacePreset:
          workspacePreset =>
            set({
              workspacePreset,

              ...presetState(
                workspacePreset
              ),

              lastActivity:
                (
                  "workspace preset "
                  + workspacePreset
                )
            }),

        toggleLeftPanel:
          () => {
            const visible =
              !get().leftPanelVisible

            set({
              leftPanelVisible:
                visible,

              lastActivity:
                visible
                  ? "tool rail opened"
                  : "tool rail hidden"
            })
          },

        toggleRightPanel:
          () => {
            const visible =
              !get().rightPanelVisible

            set({
              rightPanelVisible:
                visible,

              lastActivity:
                visible
                  ? "context inspector opened"
                  : "context inspector hidden"
            })
          },

        toggleStatusbar:
          () => {
            const visible =
              !get().statusbarVisible

            set({
              statusbarVisible:
                visible,

              lastActivity:
                visible
                  ? "status rail opened"
                  : "status rail hidden"
            })
          },

        restoreWorkspace:
          () =>
            set({
              workspacePreset:
                "conversation",

              workspaceMode:
                "single",

              focusMode:
                false,

              density:
                "comfortable",

              leftPanelVisible:
                true,

              rightPanelVisible:
                true,

              statusbarVisible:
                true,

              lastActivity:
                "workspace restored"
            }),

        setComposerDraft:
          composerDraft =>
            set({
              composerDraft
            }),

        stageTerminal:
          text =>
            set({
              terminalStage: {
                id:
                  Date.now(),

                text
              },

              workspaceMode:
                "chat-terminal-split",

              lastActivity:
                "terminal input staged"
            }),

        clearTerminalStage:
          () =>
            set({
              terminalStage:
                null
            }),

        setLastActivity:
          lastActivity =>
            set({
              lastActivity
            }),

        openSource:
          path =>
            set({
              sourcePath:
                path,

              active:
                "source",

              workspaceMode:
                "single",

              lastActivity:
                `opened ${path}`
            }),

        addUploadedContext:
          value =>
            set(
              state => {
                const existing =
                  new Set(
                    state
                      .uploadedContext
                      .map(
                        item =>
                          item.id
                      )
                  )

                const next =
                  value.filter(
                    item =>
                      !existing.has(
                        item.id
                      )
                  )

                return {
                  uploadedContext: [
                    ...state.uploadedContext,
                    ...next
                  ].slice(
                    -30
                  ),

                  lastActivity:
                    (
                      `${next.length} `
                      + "attachment"
                      + (
                        next.length
                        === 1
                          ? ""
                          : "s"
                      )
                      + " added"
                    )
                }
              }
            ),

        removeUploadedContext:
          id =>
            set(
              state => ({
                uploadedContext:
                  state
                    .uploadedContext
                    .filter(
                      item =>
                        item.id
                        !== id
                    )
              })
            ),

        clearUploadedContext:
          () =>
            set({
              uploadedContext:
                []
            })
      }),
      {
        name:
          "palaver-workspace-v9",

        partialize:
          state => ({
            active:
              state.active,

            focusMode:
              state.focusMode,

            density:
              state.density,

            workspaceMode:
              state.workspaceMode,

            workspacePreset:
              state.workspacePreset,

            leftPanelVisible:
              state.leftPanelVisible,

            rightPanelVisible:
              state.rightPanelVisible,

            statusbarVisible:
              state.statusbarVisible,

            sourcePath:
              state.sourcePath
          }),

        version:
          9,

        migrate:
          persisted => {
            const value =
              persisted as any

            if (
              value?.active
              === "uploads"
            ) {
              value.active =
                "chat"
            }

            if (
              value?.density
              !== "compact"
              && value?.density
              !== "comfortable"
              && value?.density
              !== "expert"
            ) {
              value.density =
                "comfortable"
            }

            if (
              !value?.workspacePreset
            ) {
              value.workspacePreset =
                "conversation"
            }

            if (
              typeof value
                ?.leftPanelVisible
              !== "boolean"
            ) {
              value.leftPanelVisible =
                true
            }

            if (
              typeof value
                ?.rightPanelVisible
              !== "boolean"
            ) {
              value.rightPanelVisible =
                true
            }

            if (
              typeof value
                ?.statusbarVisible
              !== "boolean"
            ) {
              value.statusbarVisible =
                true
            }

            return value
          }
      }
    )
  )
