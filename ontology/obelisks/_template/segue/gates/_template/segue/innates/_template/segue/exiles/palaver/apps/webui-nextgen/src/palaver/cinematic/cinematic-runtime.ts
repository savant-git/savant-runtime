import gsap from "gsap"


type Cleanup = () => void


const rootSelector =
  "#root"


const interactiveSelector = [
  ".rail-item",
  ".command-trigger",
  ".contextarium-controls nav button",
  ".kindred-controls nav button",
  ".search-scopes button",
  ".source-header button",
  ".module-hero button",
  ".kindred-selected > button",
  ".upload-list button"
].join(",")


const panelSelector = [
  ".memory-capsule article",
  ".forest-columns article",
  ".work-cards article",
  ".system-friendly-grid article",
  ".kindred-relations > article",
  ".search-results article",
  ".upload-row"
].join(",")


const revealSelector = [
  ".contextarium-header h1",
  ".source-header h1",
  ".kindred-title h1",
  ".universal-search > header h1",
  ".uploads-module > header h1",
  ".module-hero h1"
].join(",")


function reducedMotion() {
  return window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches
}


function finePointer() {
  return window.matchMedia(
    "(pointer: fine)"
  ).matches
}


function clamp(
  value: number,
  min: number,
  max: number
) {
  return Math.max(
    min,
    Math.min(
      max,
      value
    )
  )
}


function elementCenter(
  element: HTMLElement
) {
  const rect =
    element.getBoundingClientRect()

  return {
    x:
      rect.left
      + rect.width / 2,

    y:
      rect.top
      + rect.height / 2
  }
}


function installAtmosphere(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
    || !finePointer()
  ) {
    return () => {}
  }

  const move = (
    event: PointerEvent
  ) => {
    const x =
      event.clientX
      / window.innerWidth

    const y =
      event.clientY
      / window.innerHeight

    root.style.setProperty(
      "--palaver-pointer-x",
      `${x * 100}%`
    )

    root.style.setProperty(
      "--palaver-pointer-y",
      `${y * 100}%`
    )

    root.style.setProperty(
      "--palaver-pointer-xn",
      String(x - .5)
    )

    root.style.setProperty(
      "--palaver-pointer-yn",
      String(y - .5)
    )
  }

  window.addEventListener(
    "pointermove",
    move,
    {
      passive: true
    }
  )

  return () =>
    window.removeEventListener(
      "pointermove",
      move
    )
}


function installMagnetism(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
    || !finePointer()
  ) {
    return () => {}
  }

  const attached =
    new WeakSet<Element>()

  const cleanups:
    Cleanup[] = []


  const attach = (
    element: Element
  ) => {
    if (
      attached.has(element)
      || !(element instanceof HTMLElement)
    ) {
      return
    }

    attached.add(element)

    const move = (
      event: PointerEvent
    ) => {
      const center =
        elementCenter(
          element
        )

      const dx =
        event.clientX
        - center.x

      const dy =
        event.clientY
        - center.y

      gsap.to(
        element,
        {
          x:
            clamp(
              dx * .12,
              -7,
              7
            ),

          y:
            clamp(
              dy * .12,
              -5,
              5
            ),

          duration:
            .24,

          ease:
            "power3.out",

          overwrite:
            true
        }
      )
    }


    const leave = () => {
      gsap.to(
        element,
        {
          x: 0,
          y: 0,

          duration:
            .5,

          ease:
            "elastic.out(1, .45)",

          overwrite:
            true
        }
      )
    }


    element.addEventListener(
      "pointermove",
      move
    )

    element.addEventListener(
      "pointerleave",
      leave
    )


    cleanups.push(
      () => {
        element.removeEventListener(
          "pointermove",
          move
        )

        element.removeEventListener(
          "pointerleave",
          leave
        )

        gsap.killTweensOf(
          element
        )
      }
    )
  }


  const scan = () => {
    root
      .querySelectorAll(
        interactiveSelector
      )
      .forEach(
        attach
      )
  }


  scan()


  const observer =
    new MutationObserver(
      scan
    )

  observer.observe(
    root,
    {
      childList: true,
      subtree: true
    }
  )


  return () => {
    observer.disconnect()

    cleanups.forEach(
      cleanup =>
        cleanup()
    )
  }
}


function installPanelDepth(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
    || !finePointer()
  ) {
    return () => {}
  }

  const attached =
    new WeakSet<Element>()

  const cleanups:
    Cleanup[] = []


  const attach = (
    element: Element
  ) => {
    if (
      attached.has(element)
      || !(element instanceof HTMLElement)
    ) {
      return
    }

    attached.add(element)


    const move = (
      event: PointerEvent
    ) => {
      const rect =
        element
          .getBoundingClientRect()

      if (
        rect.width <= 0
        || rect.height <= 0
      ) {
        return
      }

      const x =
        (
          event.clientX
          - rect.left
        )
        / rect.width

      const y =
        (
          event.clientY
          - rect.top
        )
        / rect.height


      const rotateY =
        (
          x - .5
        ) * 3.4

      const rotateX =
        (
          .5 - y
        ) * 3


      element.style.setProperty(
        "--panel-light-x",
        `${x * 100}%`
      )

      element.style.setProperty(
        "--panel-light-y",
        `${y * 100}%`
      )


      gsap.to(
        element,
        {
          rotateX,
          rotateY,
          z: 5,

          transformPerspective:
            850,

          transformOrigin:
            "50% 50%",

          duration:
            .35,

          ease:
            "power3.out",

          overwrite:
            true
        }
      )
    }


    const leave = () => {
      gsap.to(
        element,
        {
          rotateX: 0,
          rotateY: 0,
          z: 0,

          duration:
            .65,

          ease:
            "power3.out",

          overwrite:
            true
        }
      )
    }


    element.addEventListener(
      "pointermove",
      move
    )

    element.addEventListener(
      "pointerleave",
      leave
    )


    cleanups.push(
      () => {
        element.removeEventListener(
          "pointermove",
          move
        )

        element.removeEventListener(
          "pointerleave",
          leave
        )

        gsap.killTweensOf(
          element
        )
      }
    )
  }


  const scan = () => {
    root
      .querySelectorAll(
        panelSelector
      )
      .forEach(
        attach
      )
  }


  scan()


  const observer =
    new MutationObserver(
      scan
    )

  observer.observe(
    root,
    {
      subtree: true,
      childList: true
    }
  )


  return () => {
    observer.disconnect()

    cleanups.forEach(
      cleanup =>
        cleanup()
    )
  }
}


function installModuleTransitions(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
  ) {
    return () => {}
  }

  let current:
    HTMLElement | null =
      null


  const candidates = [
    ".contextarium",
    ".source-studio",
    ".kindred-module",
    ".universal-search",
    ".uploads-module",
    ".work-dashboard",
    ".system-dashboard",
    ".plain-module"
  ].join(",")


  const reveal = () => {
    const candidate =
      root.querySelector(
        candidates
      )

    const next =
      candidate instanceof HTMLElement
        ? candidate
        : null


    if (
      !next
      || next === current
    ) {
      return
    }


    current =
      next


    gsap.fromTo(
      next,
      {
        opacity:
          .25,

        scale:
          .992,

        filter:
          "blur(7px)",

        y:
          8
      },
      {
        opacity:
          1,

        scale:
          1,

        filter:
          "blur(0px)",

        y:
          0,

        duration:
          .58,

        ease:
          "expo.out",

        clearProps:
          "transform,filter,opacity"
      }
    )
  }


  reveal()


  const observer =
    new MutationObserver(
      reveal
    )

  observer.observe(
    root,
    {
      childList: true,
      subtree: true
    }
  )


  return () => {
    observer.disconnect()

    if (current) {
      gsap.killTweensOf(
        current
      )
    }
  }
}


function installHeadingReveal(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
  ) {
    return () => {}
  }

  const seen =
    new WeakSet<Element>()


  const scan = () => {
    root
      .querySelectorAll(
        revealSelector
      )
      .forEach(
        element => {
          if (
            seen.has(element)
          ) {
            return
          }

          seen.add(element)

          gsap.fromTo(
            element,
            {
              yPercent:
                38,

              opacity:
                0,

              clipPath:
                "inset(100% 0 0 0)"
            },
            {
              yPercent:
                0,

              opacity:
                1,

              clipPath:
                "inset(0% 0 0 0)",

              duration:
                .72,

              ease:
                "expo.out",

              delay:
                .04
            }
          )
        }
      )
  }


  scan()


  const observer =
    new MutationObserver(
      scan
    )

  observer.observe(
    root,
    {
      subtree: true,
      childList: true
    }
  )


  return () => {
    observer.disconnect()
  }
}


function installRailSignal(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
  ) {
    return () => {}
  }

  const cleanups:
    Cleanup[] = []

  const attached =
    new WeakSet<Element>()


  const attach = (
    element: Element
  ) => {
    if (
      attached.has(element)
      || !(element instanceof HTMLElement)
    ) {
      return
    }

    attached.add(element)


    const enter = () => {
      gsap.to(
        element,
        {
          "--rail-signal":
            "100%",

          duration:
            .42,

          ease:
            "power3.out"
        }
      )
    }


    const leave = () => {
      gsap.to(
        element,
        {
          "--rail-signal":
            "0%",

          duration:
            .52,

          ease:
            "power3.out"
        }
      )
    }


    element.addEventListener(
      "pointerenter",
      enter
    )

    element.addEventListener(
      "pointerleave",
      leave
    )


    cleanups.push(
      () => {
        element.removeEventListener(
          "pointerenter",
          enter
        )

        element.removeEventListener(
          "pointerleave",
          leave
        )

        gsap.killTweensOf(
          element
        )
      }
    )
  }


  const scan = () => {
    root
      .querySelectorAll(
        ".rail-item"
      )
      .forEach(
        attach
      )
  }


  scan()


  const observer =
    new MutationObserver(
      scan
    )

  observer.observe(
    root,
    {
      subtree: true,
      childList: true
    }
  )


  return () => {
    observer.disconnect()

    cleanups.forEach(
      cleanup =>
        cleanup()
    )
  }
}


function installEnergyPulse(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
  ) {
    return () => {}
  }


  const down = (
    event: PointerEvent
  ) => {
    if (
      !(event.target instanceof Element)
    ) {
      return
    }


    const target =
      event.target.closest(
        [
          "button",
          ".memory-cell",
          ".search-results article",
          ".upload-row"
        ].join(",")
      )


    if (
      !(target instanceof HTMLElement)
    ) {
      return
    }


    const rect =
      target
        .getBoundingClientRect()


    const pulse =
      document.createElement(
        "span"
      )


    pulse.className =
      "palaver-energy-pulse"


    pulse.style.left =
      `${
        event.clientX
        - rect.left
      }px`


    pulse.style.top =
      `${
        event.clientY
        - rect.top
      }px`


    target.classList.add(
      "palaver-pulse-host"
    )


    target.appendChild(
      pulse
    )


    gsap.fromTo(
      pulse,
      {
        scale:
          0,

        opacity:
          .65
      },
      {
        scale:
          14,

        opacity:
          0,

        duration:
          .7,

        ease:
          "power3.out",

        onComplete:
          () => {
            pulse.remove()
          }
      }
    )
  }


  root.addEventListener(
    "pointerdown",
    down
  )


  return () => {
    root.removeEventListener(
      "pointerdown",
      down
    )
  }
}


function installScrollKinetics(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
  ) {
    return () => {}
  }


  const selectors = [
    ".memory-stream > div",
    ".kindred-elements > div",
    ".search-results",
    ".rail-file-list",
    ".upload-list > div"
  ].join(",")


  const attached =
    new WeakSet<Element>()

  const cleanups:
    Cleanup[] = []


  const attach = (
    element: Element
  ) => {
    if (
      attached.has(element)
      || !(element instanceof HTMLElement)
    ) {
      return
    }

    attached.add(element)


    let previous =
      element.scrollTop

    let frame =
      0


    const scroll = () => {
      cancelAnimationFrame(
        frame
      )


      frame =
        requestAnimationFrame(
          () => {
            const delta =
              element.scrollTop
              - previous

            previous =
              element.scrollTop


            const skew =
              clamp(
                delta * -.035,
                -1.4,
                1.4
              )


            gsap.to(
              element,
              {
                skewY:
                  skew,

                duration:
                  .12,

                ease:
                  "power2.out",

                overwrite:
                  true,

                onComplete:
                  () => {
                    gsap.to(
                      element,
                      {
                        skewY:
                          0,

                        duration:
                          .35,

                        ease:
                          "power3.out"
                      }
                    )
                  }
              }
            )
          }
        )
    }


    element.addEventListener(
      "scroll",
      scroll,
      {
        passive: true
      }
    )


    cleanups.push(
      () => {
        cancelAnimationFrame(
          frame
        )

        element.removeEventListener(
          "scroll",
          scroll
        )

        gsap.killTweensOf(
          element
        )
      }
    )
  }


  const scan = () => {
    root
      .querySelectorAll(
        selectors
      )
      .forEach(
        attach
      )
  }


  scan()


  const observer =
    new MutationObserver(
      scan
    )

  observer.observe(
    root,
    {
      childList: true,
      subtree: true
    }
  )


  return () => {
    observer.disconnect()

    cleanups.forEach(
      cleanup =>
        cleanup()
    )
  }
}


function installActiveTrace(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
  ) {
    return () => {}
  }


  const scan = () => {
    root
      .querySelectorAll(
        ".active, .selected, .captured"
      )
      .forEach(
        element => {
          if (
            element instanceof HTMLElement
          ) {
            element.classList.add(
              "palaver-traced"
            )
          }
        }
      )
  }


  scan()


  const observer =
    new MutationObserver(
      scan
    )


  observer.observe(
    root,
    {
      attributes:
        true,

      subtree:
        true,

      childList:
        true,

      attributeFilter: [
        "class"
      ]
    }
  )


  return () => {
    observer.disconnect()
  }
}


function installSpatialDrift(
  root: HTMLElement
): Cleanup {
  if (
    reducedMotion()
  ) {
    return () => {}
  }


  const tween =
    gsap.to(
      root,
      {
        "--palaver-phase":
          "100%",

        duration:
          24,

        repeat:
          -1,

        yoyo:
          true,

        ease:
          "sine.inOut"
      }
    )


  return () => {
    tween.kill()
  }
}


export function installPalaverCinematics() {
  const candidate =
    document.querySelector(
      rootSelector
    )


  if (
    !(candidate instanceof HTMLElement)
  ) {
    return () => {}
  }


  const root =
    candidate


  root.classList.add(
    "palaver-cinematic-runtime"
  )


  const cleanups = [
    installAtmosphere(
      root
    ),

    installMagnetism(
      root
    ),

    installPanelDepth(
      root
    ),

    installModuleTransitions(
      root
    ),

    installHeadingReveal(
      root
    ),

    installRailSignal(
      root
    ),

    installEnergyPulse(
      root
    ),

    installScrollKinetics(
      root
    ),

    installActiveTrace(
      root
    ),

    installSpatialDrift(
      root
    )
  ]


  return () => {
    cleanups.forEach(
      cleanup =>
        cleanup()
    )

    root.classList.remove(
      "palaver-cinematic-runtime"
    )
  }
}
