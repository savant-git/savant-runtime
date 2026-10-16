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

function Earth({
  quality,
  reducedMotion
}) {
  const meshRef =
    useRef(null);

  useFrame(
    (
      _state,
      delta
    ) => {
      if (
        !meshRef.current ||
        reducedMotion
      ) {
        return;
      }

      meshRef.current.rotation.y +=
        delta * 0.01;
    }
  );

  return (
    <group
      position={[
        -4.7,
        -0.7,
        -8.4
      ]}
      rotation={[
        0.08,
        0,
        -0.25
      ]}
    >
      <mesh
        ref={meshRef}
      >
        <sphereGeometry
          args={[
            3.2,
            quality.tier ===
            "low"
              ? 32
              : 56,
            quality.tier ===
            "low"
              ? 24
              : 40
          ]}
        />

        <meshStandardMaterial
          color="#12324d"
          roughness={0.78}
          metalness={0}
        />
      </mesh>

      <mesh
        scale={1.025}
      >
        <sphereGeometry
          args={[
            3.2,
            quality.tier ===
            "low"
              ? 28
              : 48,
            quality.tier ===
            "low"
              ? 20
              : 36
          ]}
        />

        <meshBasicMaterial
          color="#42a9ff"
          transparent
          opacity={
            quality.tier ===
            "low"
              ? 0.055
              : 0.09
          }
          blending={
            THREE.AdditiveBlending
          }
          side={
            THREE.BackSide
          }
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

function Moon({
  quality,
  reducedMotion
}) {
  const meshRef =
    useRef(null);

  useFrame(
    (
      _state,
      delta
    ) => {
      if (
        !meshRef.current ||
        reducedMotion
      ) {
        return;
      }

      meshRef.current.rotation.y +=
        delta * 0.003;
    }
  );

  return (
    <group
      position={[
        5.1,
        0.65,
        -10.5
      ]}
    >
      <mesh
        ref={meshRef}
      >
        <sphereGeometry
          args={[
            1.55,
            quality.tier ===
            "low"
              ? 28
              : 48,
            quality.tier ===
            "low"
              ? 20
              : 36
          ]}
        />

        <meshStandardMaterial
          color="#85837d"
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
  return (
    <mesh
      position={[
        8.8,
        3.2,
        -18
      ]}
    >
      <sphereGeometry
        args={[
          0.72,
          quality.tier ===
          "low"
            ? 20
            : 32,
          quality.tier ===
          "low"
            ? 16
            : 24
        ]}
      />

      <meshStandardMaterial
        color="#843621"
        roughness={0.94}
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
            ? 0.22
            : 0.12
        }
      />

      <hemisphereLight
        args={[
          "#8dbdff",
          "#020305",
          quality.tier ===
          "low"
            ? 0.32
            : 0.2
        ]}
      />

      <directionalLight
        position={[
          6,
          5,
          4
        ]}
        color="#fff2d9"
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

      {quality.tier !==
        "low" && (
        <Mars
          quality={quality}
        />
      )}

      <CinematicSpacecraftDetail
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

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
            ? 0.75
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
              ? 110
              : 200
        }}
        gl={{
          antialias:
            !low,
          alpha: false,
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
            0x010205,
            1
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
        </Suspense>
      </Canvas>
    </div>
  );
}
