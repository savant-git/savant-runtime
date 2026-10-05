import {
  ReactNode,
  useEffect
} from "react"

import {
  autoUpdate,
  flip,
  FloatingFocusManager,
  FloatingPortal,
  offset,
  shift,
  size,
  useClick,
  useDismiss,
  useFloating,
  useInteractions,
  useRole
} from "@floating-ui/react"

import {
  Plus
} from "lucide-react"


type Props = {
  open:
    boolean

  onOpenChange: (
    value:
      boolean
  ) => void

  children:
    ReactNode
}


export default function ChatToolSurface({
  open,
  onOpenChange,
  children
}: Props) {
  const {
    refs,
    floatingStyles,
    context
  } = useFloating({
    open,

    onOpenChange,

    placement:
      "top-start",

    whileElementsMounted:
      autoUpdate,

    middleware: [
      offset(
        10
      ),

      flip({
        fallbackAxisSideDirection:
          "end",

        padding:
          10
      }),

      shift({
        padding:
          10
      }),

      size({
        padding:
          10,

        apply({
          availableHeight,
          elements
        }) {
          Object.assign(
            elements
              .floating
              .style,
            {
              maxHeight:
                `${Math.max(
                  260,
                  Math.min(
                    availableHeight,
                    620
                  )
                )}px`
            }
          )
        }
      })
    ]
  })


  const click =
    useClick(
      context
    )

  const dismiss =
    useDismiss(
      context,
      {
        escapeKey:
          true,

        outsidePress:
          true
      }
    )

  const role =
    useRole(
      context,
      {
        role:
          "dialog"
      }
    )

  const {
    getReferenceProps,
    getFloatingProps
  } = useInteractions([
    click,
    dismiss,
    role
  ])


  useEffect(
    () => {
      if (
        !open
      ) {
        return
      }

      const close =
        () =>
          onOpenChange(
            false
          )

      window.addEventListener(
        "orientationchange",
        close
      )

      return () =>
        window.removeEventListener(
          "orientationchange",
          close
        )
    },
    [
      open,
      onOpenChange
    ]
  )


  return (
    <>
      <button
        ref={
          refs.setReference
        }
        type="button"
        className={
          open
            ? (
              "composer-plus "
              + "active"
            )
            : "composer-plus"
        }
        aria-expanded={
          open
        }
        aria-haspopup="dialog"
        aria-label={
          "Open Palaver tools"
        }
        {...getReferenceProps()}
      >
        <Plus
          size={18}
        />
      </button>

      {open
      && (
        <FloatingPortal>
          <FloatingFocusManager
            context={
              context
            }
            modal={
              false
            }
            initialFocus={
              0
            }
            returnFocus
          >
            <div
              ref={
                refs.setFloating
              }
              style={
                floatingStyles
              }
              className={
                "composer-plus-menu "
                + "palaver-floating-tools"
              }
              {...getFloatingProps()}
            >
              {children}
            </div>
          </FloatingFocusManager>
        </FloatingPortal>
      )}
    </>
  )
}
