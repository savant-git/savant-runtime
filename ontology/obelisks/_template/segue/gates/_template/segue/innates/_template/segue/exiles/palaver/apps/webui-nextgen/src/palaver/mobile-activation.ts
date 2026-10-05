type Cleanup = () => void


const actionableSelector = [
  "button",
  "a[href]",
  "[role='button']",
  "[cmdk-item]"
].join(",")


function containsPoint(
  element: HTMLElement,
  x: number,
  y: number
) {
  const rect =
    element.getBoundingClientRect()

  return (
    rect.width > 0
    && rect.height > 0
    && x >= rect.left
    && x <= rect.right
    && y >= rect.top
    && y <= rect.bottom
  )
}


function actionableAt(
  x: number,
  y: number
): HTMLElement | null {
  const candidates =
    Array.from(
      document.querySelectorAll(
        actionableSelector
      )
    )
      .filter(
        (
          element
        ): element is HTMLElement =>
          element instanceof HTMLElement
          && containsPoint(
            element,
            x,
            y
          )
      )


  if (!candidates.length) {
    return null
  }


  candidates.sort(
    (
      a,
      b
    ) => {
      const aRect =
        a.getBoundingClientRect()

      const bRect =
        b.getBoundingClientRect()

      const aArea =
        aRect.width
        * aRect.height

      const bArea =
        bRect.width
        * bRect.height

      return aArea - bArea
    }
  )


  return candidates[0]
}


function activate(
  target: HTMLElement
) {
  if (
    target instanceof HTMLButtonElement
    && target.disabled
  ) {
    return
  }


  target.focus(
    {
      preventScroll: true
    }
  )


  target.dispatchEvent(
    new MouseEvent(
      "click",
      {
        bubbles: true,
        cancelable: true,
        composed: true,
        view: window
      }
    )
  )
}


export function installMobileActivation(): Cleanup {
  let lastTarget:
    HTMLElement | null = null

  let lastActivation = 0

  let lastTouchActivation = 0


  const run = (
    x: number,
    y: number
  ) => {
    const target =
      actionableAt(
        x,
        y
      )

    if (!target) {
      return
    }


    const now =
      performance.now()


    if (
      target === lastTarget
      && now - lastActivation < 450
    ) {
      return
    }


    lastTarget =
      target

    lastActivation =
      now


    window.setTimeout(
      () => {
        activate(
          target
        )
      },
      0
    )
  }


  const pointerUp = (
    event: PointerEvent
  ) => {
    if (
      event.pointerType === "mouse"
    ) {
      return
    }

    run(
      event.clientX,
      event.clientY
    )
  }


  const touchEnd = (
    event: TouchEvent
  ) => {
    const touch =
      event.changedTouches[0]

    if (!touch) {
      return
    }


    lastTouchActivation =
      performance.now()


    run(
      touch.clientX,
      touch.clientY
    )
  }


  const clickFallback = (
    event: MouseEvent
  ) => {
    if (
      performance.now()
      - lastTouchActivation
      < 700
    ) {
      return
    }


    const direct =
      event.target instanceof Element
        ? event.target.closest(
            actionableSelector
          )
        : null


    if (
      direct instanceof HTMLElement
    ) {
      return
    }


    run(
      event.clientX,
      event.clientY
    )
  }


  document.addEventListener(
    "pointerup",
    pointerUp,
    true
  )


  document.addEventListener(
    "touchend",
    touchEnd,
    {
      capture: true,
      passive: true
    }
  )


  document.addEventListener(
    "click",
    clickFallback,
    true
  )


  return () => {
    document.removeEventListener(
      "pointerup",
      pointerUp,
      true
    )


    document.removeEventListener(
      "touchend",
      touchEnd,
      true
    )


    document.removeEventListener(
      "click",
      clickFallback,
      true
    )
  }
}
