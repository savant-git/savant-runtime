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

function seededRandom(
  seed
) {
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
  scale = 1.04
}) {
  return (
    <mesh scale={scale}>
      <sphereGeometry
        args={[
          radius,
          64,
          64
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
  scale = 1.12
}) {
  return (
    <mesh scale={scale}>
      <sphereGeometry
        args={[
          radius,
          48,
          48
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
  reducedMotion
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
          length: 190
        },
        (
          _,
          index
        ) => {
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
    }, []);

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
          0.018;
      }

      if (
        cloudLayer.current &&
        !reducedMotion
      ) {
        cloudLayer.current
          .rotation.y +=
          delta *
          0.024;
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
                    0.14
                ) *
                0.035
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
      <mesh
        ref={planet}
      >
        <sphereGeometry
          args={[
            3.2,
            128,
            128
          ]}
        />

        <meshPhysicalMaterial
          color="#102d48"
          roughness={0.72}
          metalness={0.02}
          clearcoat={0.12}
          clearcoatRoughness={
            0.7
          }
        />

        {cityLights.map(
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
                  6,
                  6
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

      <mesh
        ref={
          cloudLayer
        }
        scale={1.006}
      >
        <sphereGeometry
          args={[
            3.2,
            96,
            96
          ]}
        />

        <meshPhysicalMaterial
          color="#d9ecf4"
          transparent
          opacity={0.035}
          roughness={1}
          depthWrite={false}
        />
      </mesh>

      <Atmosphere
        radius={3.2}
        color="#52baff"
        opacity={0.12}
        scale={1.025}
      />

      <Atmosphere
        radius={3.2}
        color="#1879ff"
        opacity={0.045}
        scale={1.065}
      />

      <PlanetGlow
        radius={3.2}
        color="#1389ff"
        opacity={0.035}
        scale={1.14}
      />
    </group>
  );
}

function Moon({
  reducedMotion
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
          length: 34
        },
        (
          _,
          index
        ) => {
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
    }, []);

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
          0.004;
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
                    0.1
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
        5.15,
        0.65,
        -10.5
      ]}
    >
      <group
        ref={surface}
      >
        <mesh>
          <sphereGeometry
            args={[
              1.55,
              128,
              128
            ]}
          />

          <meshPhysicalMaterial
            color="#8b8983"
            roughness={0.97}
            metalness={0}
          />
        </mesh>

        {craters.map(
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
                  10,
                  28
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

      <PlanetGlow
        radius={1.55}
        color="#d7e4ff"
        opacity={0.025}
        scale={1.1}
      />
    </group>
  );
}

function Mars({
  reducedMotion
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
          0.006;
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
                  0.08
              ) *
              0.025
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
            72,
            72
          ]}
        />

        <meshPhysicalMaterial
          color="#8d3523"
          roughness={0.92}
        />
      </mesh>

      <PlanetGlow
        radius={0.72}
        color="#ff693d"
        opacity={0.08}
        scale={1.14}
      />
    </group>
  );
}

function CinematicLighting() {
  return (
    <>
      <ambientLight
        intensity={0.025}
      />

      <hemisphereLight
        args={[
          "#89baff",
          "#050505",
          0.09
        ]}
      />

      <directionalLight
        position={[
          4.5,
          5,
          3
        ]}
        intensity={3.8}
        color="#fff3da"
      />

      <directionalLight
        position={[
          -8,
          1,
          -2
        ]}
        intensity={0.85}
        color="#2879ff"
      />

      <pointLight
        position={[
          6,
          -2,
          -2
        ]}
        intensity={1.15}
        color="#ff9b63"
        distance={16}
      />
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
          ? 4
          : 0
      }
    >
      <Bloom
        intensity={
          reducedMotion
            ? 0.38
            : 0.64
        }
        luminanceThreshold={
          0.76
        }
        luminanceSmoothing={
          0.2
        }
        mipmapBlur
      />

      <Noise
        opacity={0.009}
        premultiply
      />

      <Vignette
        eskil={false}
        offset={0.16}
        darkness={0.66}
      />
    </EffectComposer>
  );
}

function Scene({
  mode,
  progress,
  quality,
  reducedMotion,
  cameraState
}) {
  return (
    <>
      <color
        attach="background"
        args={[
          "#010205"
        ]}
      />

      <fogExp2
        attach="fog"
        args={[
          "#02050a",
          0.009
        ]}
      />

      <CinematicEnvironment
        quality={quality}
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

      <CinematicLighting />

      <EarthDirector
        mode={mode}
      >
        <Earth
          reducedMotion={
            reducedMotion
          }
        />
      </EarthDirector>

      <MoonDirector
        mode={mode}
      >
        <Moon
          reducedMotion={
            reducedMotion
          }
        />
      </MoonDirector>

      <MarsDirector
        mode={mode}
      >
        <Mars
          reducedMotion={
            reducedMotion
          }
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

      <CinematicDepthEffects
        quality={quality}
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

      <CinematicFlightDynamics
        quality={quality}
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

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

      <CinematicFocusSystem
        quality={quality}
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

      <CinematicLensSystem
        quality={quality}
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
  mode = "transit"
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
    useMemo(
      () =>
        typeof window !==
          "undefined" &&
        window.matchMedia(
          "(prefers-reduced-motion: reduce)"
        ).matches,
      []
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
        camera={{
          position: [
            0,
            0,
            7.4
          ],
          fov: 41,
          near: 0.08,
          far: 260
        }}
        gl={{
          antialias:
            quality.tier !==
            "low",

          alpha: false,

          powerPreference:
            "high-performance",

          toneMapping:
            THREE.ACESFilmicToneMapping,

          toneMappingExposure:
            1.04
        }}
        onCreated={({
          gl
        }) => {
          gl.outputColorSpace =
            THREE.SRGBColorSpace;

          gl.shadowMap.enabled =
            Boolean(
              quality.shadows
            );

          gl.shadowMap.type =
            THREE.PCFSoftShadowMap;
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
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
