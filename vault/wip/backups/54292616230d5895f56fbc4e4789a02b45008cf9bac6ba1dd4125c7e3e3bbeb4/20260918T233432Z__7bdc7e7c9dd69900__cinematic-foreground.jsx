import {
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import {
  Float,
  Html
} from "@react-three/drei";

import {
  useFrame
} from "@react-three/fiber";

import * as THREE from "three";

const TAU = Math.PI * 2;

function seededRandom(seed) {
  let value = seed >>> 0;

  return () => {
    value += 0x6d2b79f5;

    let result = value;

    result = Math.imul(
      result ^ (result >>> 15),
      result | 1
    );

    result ^=
      result +
      Math.imul(
        result ^ (result >>> 7),
        result | 61
      );

    return (
      ((result ^ (result >>> 14)) >>> 0) /
      4294967296
    );
  };
}

function createAsteroids(
  count,
  seed
) {
  const random =
    seededRandom(seed);

  return Array.from(
    {
      length: count
    },
    (_, index) => {
      const side =
        random() > 0.5
          ? 1
          : -1;

      return {
        id: index,
        position: [
          side *
            (
              7 +
              random() * 15
            ),
          -7 +
            random() * 14,
          -5 -
            random() * 27
        ],
        scale:
          0.035 +
          Math.pow(
            random(),
            2
          ) *
            0.32,
        rotation: [
          random() * TAU,
          random() * TAU,
          random() * TAU
        ],
        velocity: [
          (
            random() - 0.5
          ) * 0.008,
          (
            random() - 0.5
          ) * 0.005,
          (
            random() - 0.5
          ) * 0.004
        ],
        spin: [
          (
            random() - 0.5
          ) * 0.18,
          (
            random() - 0.5
          ) * 0.18,
          (
            random() - 0.5
          ) * 0.18
        ],
        shape: [
          0.65 +
            random() * 0.8,
          0.65 +
            random() * 0.8,
          0.65 +
            random() * 0.8
        ]
      };
    }
  );
}

function Asteroid({
  asteroid,
  cameraState,
  reducedMotion
}) {
  const mesh = useRef();

  useFrame(
    (
      state,
      delta
    ) => {
      if (!mesh.current) {
        return;
      }

      if (!reducedMotion) {
        mesh.current.rotation.x +=
          asteroid.spin[0] *
          delta;

        mesh.current.rotation.y +=
          asteroid.spin[1] *
          delta;

        mesh.current.rotation.z +=
          asteroid.spin[2] *
          delta;

        mesh.current.position.x +=
          asteroid.velocity[0] *
          delta;

        mesh.current.position.y +=
          asteroid.velocity[1] *
          delta;

        mesh.current.position.z +=
          asteroid.velocity[2] *
          delta;
      }

      const depth =
        THREE.MathUtils.clamp(
          (
            -mesh.current
              .position.z -
            4
          ) /
            28,
          0,
          1
        );

      const parallax =
        THREE.MathUtils.lerp(
          0.72,
          0.16,
          depth
        );

      mesh.current.position.x =
        THREE.MathUtils.damp(
          mesh.current
            .position.x,
          asteroid.position[0] -
            cameraState.current
              .yaw *
              parallax *
              2.6,
          1.8,
          delta
        );

      mesh.current.position.y =
        THREE.MathUtils.damp(
          mesh.current
            .position.y,
          asteroid.position[1] +
            cameraState.current
              .pitch *
              parallax *
              1.8,
          1.8,
          delta
        );
    }
  );

  return (
    <mesh
      ref={mesh}
      position={
        asteroid.position
      }
      rotation={
        asteroid.rotation
      }
      scale={[
        asteroid.scale *
          asteroid.shape[0],
        asteroid.scale *
          asteroid.shape[1],
        asteroid.scale *
          asteroid.shape[2]
      ]}
    >
      <icosahedronGeometry
        args={[1, 1]}
      />

      <meshStandardMaterial
        color="#4b4945"
        roughness={0.97}
        metalness={0.02}
      />
    </mesh>
  );
}

function AsteroidField({
  quality,
  cameraState,
  reducedMotion
}) {
  const count =
    quality.tier === "high"
      ? 62
      : quality.tier ===
          "medium"
        ? 34
        : 16;

  const asteroids =
    useMemo(
      () =>
        createAsteroids(
          count,
          764421
        ),
      [count]
    );

  return (
    <group>
      {asteroids.map(
        asteroid => (
          <Asteroid
            key={
              asteroid.id
            }
            asteroid={
              asteroid
            }
            cameraState={
              cameraState
            }
            reducedMotion={
              reducedMotion
            }
          />
        )
      )}
    </group>
  );
}

function NavigationBeacon({
  position,
  label,
  detail,
  cameraState,
  reducedMotion
}) {
  const group = useRef();
  const [active, setActive] =
    useState(false);

  useFrame(
    (
      state,
      delta
    ) => {
      if (!group.current) {
        return;
      }

      const data =
        cameraState.current;

      group.current.rotation.y =
        THREE.MathUtils.damp(
          group.current
            .rotation.y,
          -data.yaw * 0.12,
          2,
          delta
        );

      group.current.rotation.x =
        THREE.MathUtils.damp(
          group.current
            .rotation.x,
          data.pitch * 0.08,
          2,
          delta
        );

      if (!reducedMotion) {
        group.current.rotation.z +=
          delta * 0.035;
      }
    }
  );

  return (
    <group
      ref={group}
      position={position}
    >
      <mesh
        onPointerEnter={event => {
          event.stopPropagation();
          setActive(true);
          document.body.style.cursor =
            "crosshair";
        }}
        onPointerLeave={() => {
          setActive(false);
          document.body.style.cursor =
            "";
        }}
      >
        <torusGeometry
          args={[
            0.28,
            0.006,
            8,
            64
          ]}
        />

        <meshBasicMaterial
          color={
            active
              ? "#dff4ff"
              : "#7fc7f1"
          }
          transparent
          opacity={
            active
              ? 0.85
              : 0.28
          }
          depthWrite={false}
          blending={
            THREE.AdditiveBlending
          }
          toneMapped={false}
        />
      </mesh>

      <mesh
        rotation={[
          Math.PI / 2,
          0,
          0
        ]}
      >
        <torusGeometry
          args={[
            0.19,
            0.004,
            8,
            48
          ]}
        />

        <meshBasicMaterial
          color="#a6dfff"
          transparent
          opacity={0.2}
          depthWrite={false}
          blending={
            THREE.AdditiveBlending
          }
          toneMapped={false}
        />
      </mesh>

      <pointLight
        color="#78c9ff"
        intensity={
          active
            ? 1.6
            : 0.45
        }
        distance={2}
      />

      {active && (
        <Html
          center
          distanceFactor={8}
          position={[
            0,
            0.48,
            0
          ]}
          style={{
            pointerEvents:
              "none"
          }}
        >
          <div className="cinematic-object-label">
            <span>
              {label}
            </span>

            <strong>
              {detail}
            </strong>
          </div>
        </Html>
      )}
    </group>
  );
}

function LightShaft({
  position,
  rotation,
  scale,
  opacity
}) {
  return (
    <mesh
      position={position}
      rotation={rotation}
      scale={scale}
      renderOrder={-2}
    >
      <coneGeometry
        args={[
          1,
          4,
          48,
          1,
          true
        ]}
      />

      <meshBasicMaterial
        color="#f4c996"
        transparent
        opacity={opacity}
        side={
          THREE.DoubleSide
        }
        depthWrite={false}
        blending={
          THREE.AdditiveBlending
        }
        toneMapped={false}
      />
    </mesh>
  );
}

function VolumetricIllusion({
  quality,
  reducedMotion
}) {
  const group = useRef();

  useFrame(
    (
      state,
      delta
    ) => {
      if (
        !group.current ||
        reducedMotion
      ) {
        return;
      }

      const target =
        0.98 +
        Math.sin(
          state.clock
            .elapsedTime *
            0.23
        ) *
          0.018;

      group.current.scale.x =
        THREE.MathUtils.damp(
          group.current
            .scale.x,
          target,
          1.5,
          delta
        );

      group.current.scale.y =
        group.current.scale.x;

      group.current.scale.z =
        group.current.scale.x;
    }
  );

  if (
    quality.tier === "low"
  ) {
    return null;
  }

  return (
    <group ref={group}>
      <LightShaft
        position={[
          -3.8,
          2.8,
          -10
        ]}
        rotation={[
          -0.15,
          0,
          -0.82
        ]}
        scale={[
          0.42,
          2.6,
          0.42
        ]}
        opacity={0.012}
      />

      {quality.tier ===
        "high" && (
        <LightShaft
          position={[
            -4.1,
            2.65,
            -11
          ]}
          rotation={[
            -0.08,
            0.04,
            -0.78
          ]}
          scale={[
            0.72,
            3.2,
            0.72
          ]}
          opacity={0.007}
        />
      )}
    </group>
  );
}

function ProximityField({
  cameraState,
  reducedMotion
}) {
  const group = useRef();

  useFrame(
    (
      state,
      delta
    ) => {
      if (!group.current) {
        return;
      }

      const data =
        cameraState.current;

      group.current.position.x =
        THREE.MathUtils.damp(
          group.current
            .position.x,
          -data.yaw * 1.1,
          3,
          delta
        );

      group.current.position.y =
        THREE.MathUtils.damp(
          group.current
            .position.y,
          data.pitch * 0.7,
          3,
          delta
        );

      if (!reducedMotion) {
        group.current.rotation.z =
          Math.sin(
            state.clock
              .elapsedTime *
              0.09
          ) * 0.012;
      }
    }
  );

  return (
    <group ref={group}>
      <Float
        speed={
          reducedMotion
            ? 0
            : 0.6
        }
        rotationIntensity={
          reducedMotion
            ? 0
            : 0.1
        }
        floatIntensity={
          reducedMotion
            ? 0
            : 0.12
        }
      >
        <NavigationBeacon
          position={[
            -1.8,
            1.15,
            -4.7
          ]}
          label="EARTH DEPARTURE"
          detail="CISLUNAR VECTOR"
          cameraState={
            cameraState
          }
          reducedMotion={
            reducedMotion
          }
        />
      </Float>

      <Float
        speed={
          reducedMotion
            ? 0
            : 0.48
        }
        rotationIntensity={
          reducedMotion
            ? 0
            : 0.08
        }
        floatIntensity={
          reducedMotion
            ? 0
            : 0.09
        }
      >
        <NavigationBeacon
          position={[
            4.4,
            1.5,
            -7.4
          ]}
          label="LUNAR SPACE"
          detail="DESTINATION FIELD"
          cameraState={
            cameraState
          }
          reducedMotion={
            reducedMotion
          }
        />
      </Float>
    </group>
  );
}

export default function CinematicForeground({
  quality,
  cameraState,
  reducedMotion
}) {
  useEffect(
    () => () => {
      document.body.style.cursor =
        "";
    },
    []
  );

  return (
    <>
      <AsteroidField
        quality={quality}
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

      <VolumetricIllusion
        quality={quality}
        reducedMotion={
          reducedMotion
        }
      />

      <ProximityField
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />
    </>
  );
}
