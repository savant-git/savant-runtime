import {
  Suspense,
  useEffect,
  useMemo,
  useRef
} from "react";

import {
  Canvas,
  useFrame
} from "@react-three/fiber";

import {
  Bloom,
  EffectComposer,
  Noise,
  Vignette
} from "@react-three/postprocessing";

import * as THREE from "three";

import {
  CinematicCameraRig,
  CinematicEnvironment,
  createCameraState
} from "./cinematic-environment.jsx";

import CinematicForeground from "./cinematic-foreground.jsx";
import CinematicDepthEffects from "./cinematic-depth-effects.jsx";
import CinematicFlightDynamics from "./cinematic-flight-dynamics.jsx";
import CinematicOrbitalNavigation from "./cinematic-orbital-navigation.jsx";
import CinematicSpacecraftDetail from "./cinematic-spacecraft-detail.jsx";
import CinematicLensSystem from "./cinematic-lens-system.jsx";
import CinematicFocusSystem from "./cinematic-focus-system.jsx";
import CinematicCameraTargeting from "./cinematic-camera-targeting.jsx";
import CinematicReticleSystem from "./cinematic-reticle-system.jsx";
import CinematicRuntimeGovernor from "./cinematic-runtime-governor.jsx";

import {
  EarthDirector,
  ForegroundDirector,
  MarsDirector,
  MoonDirector,
  OrbitalDirector,
  SpacecraftDirector
} from "./cinematic-scene-director.jsx";

import {
  getQualityProfile
} from "../lib/quality.js";

const TAU =
  Math.PI * 2;

function seededRandom(seed) {
  let value =
    seed >>> 0;

  return () => {
    value +=
      0x6d2b79f5;

    let result =
      value;

    result =
      Math.imul(
        result ^
          (result >>> 15),
        result | 1
      );

    result ^=
      result +
      Math.imul(
        result ^
          (result >>> 7),
        result | 61
      );

    return (
      (
        result ^
        (result >>> 14)
      ) >>>
      0
    ) /
      4294967296;
  };
}

function Atmosphere({
  radius,
  color,
  opacity = 0.15,
  scale = 1.04,
  segments = 32
}) {
  return (
    <mesh scale={scale}>
      <sphereGeometry
        args={[
          radius,
          segments,
          segments
        ]}
      />

      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        blending={
          THREE.AdditiveBlending
        }
        side={
          THREE.BackSide
        }
        depthWrite={false}
      />
    </mesh>
  );
}

function PlanetGlow({
  radius,
  color,
  opacity = 0.18,
  scale = 1.12,
  segments = 28
}) {
  return (
    <mesh scale={scale}>
      <sphereGeometry
        args={[
          radius,
          segments,
          segments
        ]}
      />

      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        blending={
          THREE.AdditiveBlending
        }
        side={
          THREE.BackSide
        }
        depthWrite={false}
      />
    </mesh>
  );
}

function Earth({
  reducedMotion,
  quality
}) {
  const group =
    useRef();

  const planet =
    useRef();

  const cloudLayer =
    useRef();

  const cityLights =
    useMemo(() => {
      const random =
        seededRandom(
          14321
        );

      return Array.from(
        {
          length:
            quality.cityLights
        },
        (_, index) => {
          const phi =
            Math.acos(
              2 *
                random() -
                1
            );

          const theta =
            TAU *
            random();

          const radius =
            3.225;

          return {
            id: index,

            position: [
              radius *
                Math.sin(
                  phi
                ) *
                Math.cos(
                  theta
                ),

              radius *
                Math.cos(
                  phi
                ),

              radius *
                Math.sin(
                  phi
                ) *
                Math.sin(
                  theta
                )
            ],

            size:
              0.025 +
              random() *
                0.07,

            intensity:
              0.15 +
              random() *
                0.55
          };
        }
      );
    }, [
      quality.cityLights
    ]);

  useFrame(
    (
      state,
      delta
    ) => {
      if (
        planet.current &&
        !reducedMotion
      ) {
        planet.current
          .rotation.y +=
          delta *
          0.012;
      }

      if (
        cloudLayer.current &&
        !reducedMotion
      ) {
        cloudLayer.current
          .rotation.y +=
          delta *
          0.017;
      }

      if (
        group.current
      ) {
        group.current
          .position.y =
          -0.65 +
          (
            reducedMotion
              ? 0
              : Math.sin(
                  state.clock
                    .elapsedTime *
                    0.12
                ) *
                0.025
          );
      }
    }
  );

  return (
    <group
      ref={group}
      position={[
        -4.85,
        -0.65,
        -8.2
      ]}
      rotation={[
        0.08,
        0,
        -0.25
      ]}
    >
      <mesh ref={planet}>
        <sphereGeometry
          args={[
            3.2,
            quality.planetSegments,
            quality.planetSegments
          ]}
        />

        <meshStandardMaterial
          color="#102d48"
          roughness={0.74}
          metalness={0.01}
        />

        {quality.tier !==
          "low" &&
          cityLights.map(
            light => (
              <mesh
                key={
                  light.id
                }
                position={
                  light.position
                }
                scale={
                  light.size
                }
              >
                <sphereGeometry
                  args={[
                    1,
                    4,
                    4
                  ]}
                />

                <meshBasicMaterial
                  color="#d6a95d"
                  transparent
                  opacity={
                    light.intensity
                  }
                  blending={
                    THREE.AdditiveBlending
                  }
                  depthWrite={
                    false
                  }
                />
              </mesh>
            )
          )}
      </mesh>

      {quality.tier ===
        "high" && (
        <mesh
          ref={
            cloudLayer
          }
          scale={1.006}
        >
          <sphereGeometry
            args={[
              3.2,
              quality.planetSegments,
              quality.planetSegments
            ]}
          />

          <meshStandardMaterial
            color="#d9ecf4"
            transparent
            opacity={0.03}
            roughness={1}
            depthWrite={
              false
            }
          />
        </mesh>
      )}

      <Atmosphere
        radius={3.2}
        color="#52baff"
        opacity={
          quality.tier ===
          "low"
            ? 0.055
            : 0.1
        }
        scale={1.025}
        segments={
          quality.detailSegments
        }
      />

      {quality.tier ===
        "high" && (
        <PlanetGlow
          radius={3.2}
          color="#1389ff"
          opacity={0.025}
          scale={1.12}
          segments={
            quality.detailSegments
          }
        />
      )}
    </group>
  );
}

function Moon({
  reducedMotion,
  quality
}) {
  const group =
    useRef();

  const surface =
    useRef();

  const craters =
    useMemo(() => {
      const random =
        seededRandom(
          8821
        );

      return Array.from(
        {
          length:
            quality.moonCraters
        },
        (_, index) => {
          const theta =
            random() *
            TAU;

          const phi =
            0.28 +
            random() *
              (
                Math.PI -
                0.56
              );

          const radius =
            1.565;

          const position =
            new THREE.Vector3(
              radius *
                Math.sin(
                  phi
                ) *
                Math.cos(
                  theta
                ),

              radius *
                Math.cos(
                  phi
                ),

              radius *
                Math.sin(
                  phi
                ) *
                Math.sin(
                  theta
                )
            );

          const normal =
            position
              .clone()
              .normalize();

          const quaternion =
            new THREE.Quaternion()
              .setFromUnitVectors(
                new THREE.Vector3(
                  0,
                  0,
                  1
                ),
                normal
              );

          const rotation =
            new THREE.Euler()
              .setFromQuaternion(
                quaternion
              );

          return {
            id: index,

            position:
              position.toArray(),

            rotation: [
              rotation.x,
              rotation.y,
              rotation.z
            ],

            scale:
              0.35 +
              random() *
                1.2
          };
        }
      );
    }, [
      quality.moonCraters
    ]);

  useFrame(
    (
      state,
      delta
    ) => {
      if (
        surface.current &&
        !reducedMotion
      ) {
        surface.current
          .rotation.y +=
          delta *
          0.003;
      }

      if (
        group.current
      ) {
        group.current
          .position.y =
          0.65 +
          (
            reducedMotion
              ? 0
              : Math.sin(
                  state.clock
                    .elapsedTime *
                    0.09
                ) *
                0.018
          );
      }
    }
  );

  return (
    <group
      ref={group}
      position={[
        5.15,
        0.65,
        -10.5
      ]}
    >
      <group ref={surface}>
        <mesh>
          <sphereGeometry
            args={[
              1.55,
              quality.moonSegments,
              quality.moonSegments
            ]}
          />

          <meshStandardMaterial
            color="#8b8983"
            roughness={0.98}
            metalness={0}
          />
        </mesh>

        {quality.tier !==
          "low" &&
          craters.map(
            crater => (
              <mesh
                key={
                  crater.id
                }
                position={
                  crater.position
                }
                rotation={
                  crater.rotation
                }
                scale={
                  crater.scale
                }
              >
                <torusGeometry
                  args={[
                    0.13,
                    0.035,
                    6,
                    14
                  ]}
                />

                <meshStandardMaterial
                  color="#5e5d5a"
                  roughness={1}
                />
              </mesh>
            )
          )}
      </group>

      {quality.tier !==
        "low" && (
        <PlanetGlow
          radius={1.55}
          color="#d7e4ff"
          opacity={0.02}
          scale={1.09}
          segments={
            quality.detailSegments
          }
        />
      )}
    </group>
  );
}

function Mars({
  reducedMotion,
  quality
}) {
  const group =
    useRef();

  useFrame(
    (
      state,
      delta
    ) => {
      if (
        !group.current
      ) {
        return;
      }

      if (
        !reducedMotion
      ) {
        group.current
          .rotation.y +=
          delta *
          0.004;
      }

      group.current
        .position.y =
        3.25 +
        (
          reducedMotion
            ? 0
            : Math.sin(
                state.clock
                  .elapsedTime *
                  0.07
              ) *
              0.016
        );
    }
  );

  return (
    <group
      ref={group}
      position={[
        8.8,
        3.25,
        -18
      ]}
    >
      <mesh>
        <sphereGeometry
          args={[
            0.72,
            quality.detailSegments,
            quality.detailSegments
          ]}
        />

        <meshStandardMaterial
          color="#8d3523"
          roughness={0.94}
        />
      </mesh>
    </group>
  );
}

function CinematicLighting({
  quality
}) {
  return (
    <>
      <ambientLight
        intensity={
          quality.tier ===
          "low"
            ? 0.1
            : 0.04
        }
      />

      <hemisphereLight
        args={[
          "#89baff",
          "#050505",
          quality.tier ===
          "low"
            ? 0.18
            : 0.1
        ]}
      />

      <directionalLight
        position={[
          4.5,
          5,
          3
        ]}
        intensity={
          quality.tier ===
          "low"
            ? 2.4
            : 3.4
        }
        color="#fff3da"
      />

      {quality.tier ===
        "high" && (
        <directionalLight
          position={[
            -8,
            1,
            -2
          ]}
          intensity={0.65}
          color="#2879ff"
        />
      )}
    </>
  );
}

function PostProcessing({
  quality,
  reducedMotion
}) {
  if (
    !quality.postprocessing ||
    quality.tier ===
      "low"
  ) {
    return null;
  }

  return (
    <EffectComposer
      multisampling={
        quality.tier ===
        "high"
          ? 2
          : 0
      }
    >
      {quality.bloom && (
        <Bloom
          intensity={
            reducedMotion
              ? 0.3
              : 0.48
          }
          luminanceThreshold={
            0.8
          }
          luminanceSmoothing={
            0.16
          }
          mipmapBlur
        />
      )}

      {quality.noise &&
        quality.tier ===
          "high" && (
          <Noise
            opacity={0.004}
            premultiply
          />
        )}

      {quality.vignette && (
        <Vignette
          eskil={false}
          offset={0.18}
          darkness={0.5}
        />
      )}
    </EffectComposer>
  );
}

function Scene({
  mode,
  progress,
  quality,
  reducedMotion,
  cameraState,
  externalMatte
}) {
  const performanceLevel =
    cameraState.current
      .performanceLevel || 0;

  return (
    <>
      <CinematicLighting
        quality={quality}
      />

      {!externalMatte && (
        <CinematicEnvironment
          quality={quality}
          cameraState={
            cameraState
          }
          reducedMotion={
            reducedMotion
          }
        />
      )}

      <EarthDirector
        mode={mode}
      >
        <Earth
          reducedMotion={
            reducedMotion
          }
          quality={quality}
        />
      </EarthDirector>

      <MoonDirector
        mode={mode}
      >
        <Moon
          reducedMotion={
            reducedMotion
          }
          quality={quality}
        />
      </MoonDirector>

      <MarsDirector
        mode={mode}
      >
        <Mars
          reducedMotion={
            reducedMotion
          }
          quality={quality}
        />
      </MarsDirector>

      <SpacecraftDirector
        mode={mode}
      >
        <CinematicSpacecraftDetail
          cameraState={
            cameraState
          }
          reducedMotion={
            reducedMotion
          }
        />
      </SpacecraftDirector>

      {quality.tier !==
        "low" && (
        <OrbitalDirector
          mode={mode}
        >
          <CinematicOrbitalNavigation
            progress={
              progress
            }
            cameraState={
              cameraState
            }
            reducedMotion={
              reducedMotion
            }
            quality={
              quality
            }
          />
        </OrbitalDirector>
      )}

      {quality.tier ===
        "high" && (
        <CinematicDepthEffects
          quality={
            quality
          }
          cameraState={
            cameraState
          }
          reducedMotion={
            reducedMotion
          }
        />
      )}

      {performanceLevel <
        2 && (
        <CinematicFlightDynamics
          quality={
            quality
          }
          cameraState={
            cameraState
          }
          reducedMotion={
            reducedMotion
          }
        />
      )}

      {quality.tier !==
        "low" &&
        performanceLevel <
          2 && (
          <ForegroundDirector
            mode={mode}
          >
            <CinematicForeground
              quality={
                quality
              }
              cameraState={
                cameraState
              }
              reducedMotion={
                reducedMotion
              }
            />
          </ForegroundDirector>
        )}

      {quality.tier ===
        "high" &&
        performanceLevel ===
          0 && (
          <CinematicFocusSystem
            quality={
              quality
            }
            cameraState={
              cameraState
            }
            reducedMotion={
              reducedMotion
            }
          />
        )}

      {quality.tier !==
        "low" &&
        performanceLevel ===
          0 && (
          <CinematicLensSystem
            quality={
              quality
            }
            cameraState={
              cameraState
            }
            reducedMotion={
              reducedMotion
            }
          />
        )}

      <CinematicReticleSystem
        reducedMotion={
          reducedMotion
        }
      />

      <CinematicCameraTargeting
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

      <CinematicCameraRig
        cameraState={
          cameraState
        }
        progress={
          progress
        }
        reducedMotion={
          reducedMotion
        }
      />

      <CinematicRuntimeGovernor
        quality={quality}
        cameraState={
          cameraState
        }
      />

      <PostProcessing
        quality={quality}
        reducedMotion={
          reducedMotion
        }
      />
    </>
  );
}

export default function SpaceScene({
  externalCameraState,
  mode = "transit",
  externalMatte = false
}) {
  const progress =
    useRef(0);

  const internalCameraState =
    useRef(
      createCameraState()
    );

  const cameraState =
    externalCameraState ??
    internalCameraState;

  const quality =
    useMemo(
      () =>
        getQualityProfile(),
      []
    );

  const reducedMotion =
    Boolean(
      quality.reducedMotion
    );

  useEffect(() => {
    function updateScroll() {
      const height =
        document
          .documentElement
          .scrollHeight -
        window.innerHeight;

      progress.current =
        height > 0
          ? THREE.MathUtils.clamp(
              window.scrollY /
                height,
              0,
              1
            )
          : 0;
    }

    updateScroll();

    window.addEventListener(
      "scroll",
      updateScroll,
      {
        passive: true
      }
    );

    window.addEventListener(
      "resize",
      updateScroll,
      {
        passive: true
      }
    );

    return () => {
      window.removeEventListener(
        "scroll",
        updateScroll
      );

      window.removeEventListener(
        "resize",
        updateScroll
      );
    };
  }, []);

  return (
    <div
      className="space-canvas"
      aria-hidden="true"
    >
      <Canvas
        dpr={quality.dpr}
        frameloop="always"
        camera={{
          position: [
            0,
            0,
            7.4
          ],
          fov: 41,
          near: 0.1,
          far:
            quality.tier ===
            "low"
              ? 100
              : 220
        }}
        gl={{
          antialias:
            quality.tier ===
            "high",

          alpha:
            externalMatte,

          powerPreference:
            "high-performance",

          stencil: false,

          depth: true,

          preserveDrawingBuffer:
            false,

          toneMapping:
            THREE.ACESFilmicToneMapping,

          toneMappingExposure:
            1
        }}
        onCreated={({
          gl
        }) => {
          gl.outputColorSpace =
            THREE.SRGBColorSpace;

          gl.setClearColor(
            0x000000,
            externalMatte
              ? 0
              : 1
          );

          gl.shadowMap.enabled =
            false;
        }}
      >
        <Suspense
          fallback={null}
        >
          <Scene
            mode={mode}
            progress={
              progress
            }
            quality={
              quality
            }
            reducedMotion={
              reducedMotion
            }
            cameraState={
              cameraState
            }
            externalMatte={
              externalMatte
            }
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
