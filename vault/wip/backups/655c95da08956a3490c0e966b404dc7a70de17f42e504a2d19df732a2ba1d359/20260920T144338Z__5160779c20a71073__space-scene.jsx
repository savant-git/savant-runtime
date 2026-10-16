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

import * as THREE from "three";

import {
  CinematicCameraRig,
  CinematicEnvironment,
  createCameraState
} from "./cinematic-environment.jsx";

import CinematicSpacecraftDetail from "./cinematic-spacecraft-detail.jsx";
import CinematicCameraTargeting from "./cinematic-camera-targeting.jsx";
import CinematicReticleSystem from "./cinematic-reticle-system.jsx";

import {
  getQualityProfile
} from "../lib/quality.js";

function PlanetAtmosphere({
  radius,
  segments,
  color,
  opacity
}) {
  return (
    <mesh
      scale={1.026}
    >
      <sphereGeometry
        args={[
          radius,
          segments,
          Math.max(
            12,
            Math.round(
              segments *
              0.72
            )
          )
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
        toneMapped={false}
      />
    </mesh>
  );
}

function Earth({
  quality,
  reducedMotion
}) {
  const surfaceRef =
    useRef(null);

  useFrame(
    (
      _state,
      delta
    ) => {
      if (
        reducedMotion ||
        !surfaceRef.current
      ) {
        return;
      }

      surfaceRef.current
        .rotation.y +=
        delta *
        0.009;
    }
  );

  const segments =
    quality.tier ===
    "low"
      ? 32
      : quality.tier ===
          "medium"
        ? 48
        : 64;

  return (
    <group
      position={[
        -4.8,
        -0.72,
        -8.8
      ]}
      rotation={[
        0.08,
        0,
        -0.25
      ]}
    >
      <mesh
        ref={surfaceRef}
      >
        <sphereGeometry
          args={[
            3.2,
            segments,
            Math.round(
              segments *
              0.72
            )
          ]}
        />

        <meshStandardMaterial
          color="#123652"
          roughness={0.74}
          metalness={0.01}
        />
      </mesh>

      <PlanetAtmosphere
        radius={3.2}
        segments={
          Math.max(
            24,
            Math.round(
              segments *
              0.75
            )
          )
        }
        color="#4ab7ff"
        opacity={
          quality.tier ===
          "low"
            ? 0.045
            : 0.075
        }
      />
    </group>
  );
}

function Moon({
  quality,
  reducedMotion
}) {
  const surfaceRef =
    useRef(null);

  useFrame(
    (
      _state,
      delta
    ) => {
      if (
        reducedMotion ||
        !surfaceRef.current
      ) {
        return;
      }

      surfaceRef.current
        .rotation.y +=
        delta *
        0.0025;
    }
  );

  const segments =
    quality.tier ===
    "low"
      ? 28
      : quality.tier ===
          "medium"
        ? 42
        : 56;

  return (
    <group
      position={[
        5.2,
        0.7,
        -10.8
      ]}
    >
      <mesh
        ref={surfaceRef}
      >
        <sphereGeometry
          args={[
            1.55,
            segments,
            Math.round(
              segments *
              0.72
            )
          ]}
        />

        <meshStandardMaterial
          color="#8a8882"
          roughness={0.98}
          metalness={0}
        />
      </mesh>
    </group>
  );
}

function Mars({
  quality
}) {
  if (
    quality.tier ===
    "low"
  ) {
    return null;
  }

  return (
    <mesh
      position={[
        9,
        3.35,
        -18
      ]}
    >
      <sphereGeometry
        args={[
          0.7,
          quality.tier ===
          "high"
            ? 36
            : 24,
          quality.tier ===
          "high"
            ? 26
            : 18
        ]}
      />

      <meshStandardMaterial
        color="#853922"
        roughness={0.95}
      />
    </mesh>
  );
}

function Lighting({
  quality
}) {
  return (
    <>
      <ambientLight
        intensity={
          quality.tier ===
          "low"
            ? 0.2
            : 0.12
        }
      />

      <hemisphereLight
        args={[
          "#82b7ff",
          "#020305",
          quality.tier ===
          "low"
            ? 0.25
            : 0.18
        ]}
      />

      <directionalLight
        position={[
          6,
          5,
          4
        ]}
        color="#fff0d3"
        intensity={
          quality.tier ===
          "low"
            ? 2.2
            : 3
        }
      />
    </>
  );
}

function Scene({
  mode,
  progress,
  quality,
  cameraState,
  reducedMotion
}) {
  return (
    <>
      <Lighting
        quality={quality}
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

      <Earth
        quality={quality}
        reducedMotion={
          reducedMotion
        }
      />

      <Moon
        quality={quality}
        reducedMotion={
          reducedMotion
        }
      />

      <Mars
        quality={quality}
      />

      <CinematicSpacecraftDetail
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

      {quality.tier !==
        "low" && (
        <CinematicReticleSystem
          reducedMotion={
            reducedMotion
          }
        />
      )}

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
        mode={mode}
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
    Boolean(
      quality.reducedMotion
    );

  useEffect(() => {
    const update =
      () => {
        const maximum =
          document
            .documentElement
            .scrollHeight -
          window.innerHeight;

        progress.current =
          maximum > 0
            ? THREE.MathUtils.clamp(
                window.scrollY /
                  maximum,
                0,
                1
              )
            : 0;
      };

    update();

    window.addEventListener(
      "scroll",
      update,
      {
        passive: true
      }
    );

    window.addEventListener(
      "resize",
      update,
      {
        passive: true
      }
    );

    return () => {
      window.removeEventListener(
        "scroll",
        update
      );

      window.removeEventListener(
        "resize",
        update
      );
    };
  }, []);

  const low =
    quality.tier ===
    "low";

  return (
    <div
      className="space-canvas"
      aria-hidden="true"
    >
      <Canvas
        dpr={
          low
            ? 0.72
            : quality.dpr
        }
        camera={{
          position: [
            0,
            0,
            7.4
          ],
          fov: 41,
          near: 0.1,
          far:
            low
              ? 100
              : 180
        }}
        gl={{
          antialias:
            quality.tier ===
            "high",
          alpha: true,
          stencil: false,
          depth: true,
          powerPreference:
            "high-performance",
          preserveDrawingBuffer:
            false
        }}
        onCreated={({
          gl
        }) => {
          gl.outputColorSpace =
            THREE.SRGBColorSpace;

          gl.toneMapping =
            THREE.ACESFilmicToneMapping;

          gl.toneMappingExposure =
            1;

          gl.shadowMap.enabled =
            false;

          gl.setClearColor(
            0x000000,
            0
          );
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
            quality={quality}
            cameraState={
              cameraState
            }
            reducedMotion={
              reducedMotion
            }
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
