import {
  useMemo,
  useRef,
  useState
} from "react";

import {
  Html
} from "@react-three/drei";

import {
  useFrame
} from "@react-three/fiber";

import * as THREE from "three";

function Panel({
  position,
  rotation = [0, 0, 0],
  scale = [1, 1, 1]
}) {
  return (
    <group
      position={position}
      rotation={rotation}
      scale={scale}
    >
      <mesh>
        <boxGeometry
          args={[
            1.55,
            0.025,
            0.62
          ]}
        />

        <meshPhysicalMaterial
          color="#112d54"
          roughness={0.34}
          metalness={0.52}
          clearcoat={0.18}
        />
      </mesh>

      {[-0.52, 0, 0.52].map(
        x => (
          <mesh
            key={x}
            position={[
              x,
              -0.016,
              0
            ]}
          >
            <boxGeometry
              args={[
                0.012,
                0.012,
                0.59
              ]}
            />

            <meshBasicMaterial
              color="#7da3c8"
              transparent
              opacity={0.24}
            />
          </mesh>
        )
      )}

      {[-0.2, 0.2].map(
        z => (
          <mesh
            key={z}
            position={[
              0,
              -0.016,
              z
            ]}
          >
            <boxGeometry
              args={[
                1.52,
                0.012,
                0.012
              ]}
            />

            <meshBasicMaterial
              color="#7da3c8"
              transparent
              opacity={0.18}
            />
          </mesh>
        )
      )}
    </group>
  );
}

function RcsThruster({
  position,
  rotation = [0, 0, 0],
  active
}) {
  return (
    <group
      position={position}
      rotation={rotation}
    >
      <mesh>
        <cylinderGeometry
          args={[
            0.035,
            0.052,
            0.11,
            16
          ]}
        />

        <meshPhysicalMaterial
          color="#34383b"
          roughness={0.34}
          metalness={0.84}
        />
      </mesh>

      {active && (
        <>
          <mesh
            position={[
              0,
              -0.09,
              0
            ]}
          >
            <coneGeometry
              args={[
                0.032,
                0.14,
                16,
                1,
                true
              ]}
            />

            <meshBasicMaterial
              color="#9fdcff"
              transparent
              opacity={0.28}
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

          <pointLight
            position={[
              0,
              -0.1,
              0
            ]}
            color="#84d7ff"
            intensity={0.55}
            distance={0.5}
          />
        </>
      )}
    </group>
  );
}

function DetailedOrion({
  cameraState,
  reducedMotion
}) {
  const root = useRef();
  const [hovered, setHovered] =
    useState(false);

  useFrame(
    (
      state,
      delta
    ) => {
      if (!root.current) {
        return;
      }

      const data =
        cameraState.current;

      if (!reducedMotion) {
        root.current.rotation.y +=
          delta * 0.055;
      }

      root.current.rotation.x =
        THREE.MathUtils.damp(
          root.current.rotation.x,
          0.08 +
            data.pitch * 0.07,
          2.5,
          delta
        );

      root.current.rotation.z =
        THREE.MathUtils.damp(
          root.current.rotation.z,
          -0.16 -
            data.yaw * 0.06,
          2.5,
          delta
        );

      const targetScale =
        hovered
          ? 0.91
          : 0.84;

      const scale =
        THREE.MathUtils.damp(
          root.current.scale.x,
          targetScale,
          6,
          delta
        );

      root.current.scale.setScalar(
        scale
      );

      root.current.position.y =
        -0.1 +
        (
          reducedMotion
            ? 0
            : Math.sin(
                state.clock
                  .elapsedTime *
                  0.47
              ) *
              0.045
        );
    }
  );

  const rcsActive =
    !reducedMotion &&
    Math.abs(
      cameraState.current
        .yawVelocity
    ) > 0.3;

  return (
    <group
      ref={root}
      position={[
        2.45,
        -0.1,
        -3.65
      ]}
      rotation={[
        0.08,
        -0.7,
        -0.16
      ]}
      scale={0.84}
      onPointerEnter={event => {
        event.stopPropagation();
        setHovered(true);
        document.body.style.cursor =
          "crosshair";
      }}
      onPointerLeave={() => {
        setHovered(false);
        document.body.style.cursor =
          "";
      }}
    >
      <mesh
        rotation={[
          0,
          0,
          Math.PI / 2
        ]}
      >
        <cylinderGeometry
          args={[
            0.38,
            0.62,
            0.76,
            64
          ]}
        />

        <meshPhysicalMaterial
          color="#d8dbda"
          roughness={0.26}
          metalness={0.7}
          clearcoat={0.34}
          clearcoatRoughness={
            0.2
          }
        />
      </mesh>

      <mesh
        position={[
          0.52,
          0,
          0
        ]}
        rotation={[
          0,
          0,
          -Math.PI / 2
        ]}
      >
        <coneGeometry
          args={[
            0.39,
            0.43,
            64
          ]}
        />

        <meshPhysicalMaterial
          color="#1e2328"
          roughness={0.18}
          metalness={0.88}
          clearcoat={0.25}
        />
      </mesh>

      <mesh
        position={[
          -0.57,
          0,
          0
        ]}
        rotation={[
          0,
          0,
          Math.PI / 2
        ]}
      >
        <cylinderGeometry
          args={[
            0.31,
            0.34,
            0.43,
            48
          ]}
        />

        <meshPhysicalMaterial
          color="#555a5e"
          roughness={0.3}
          metalness={0.82}
        />
      </mesh>

      <mesh
        position={[
          -0.82,
          0,
          0
        ]}
        rotation={[
          0,
          0,
          Math.PI / 2
        ]}
      >
        <cylinderGeometry
          args={[
            0.17,
            0.27,
            0.24,
            40
          ]}
        />

        <meshPhysicalMaterial
          color="#171b1e"
          roughness={0.22}
          metalness={0.9}
        />
      </mesh>

      <mesh
        position={[
          0.1,
          0.31,
          0.25
        ]}
        rotation={[
          0.4,
          0,
          0
        ]}
      >
        <boxGeometry
          args={[
            0.28,
            0.045,
            0.13
          ]}
        />

        <meshPhysicalMaterial
          color="#080b0d"
          roughness={0.12}
          metalness={0.2}
          transmission={0.15}
        />
      </mesh>

      <mesh
        position={[
          0.1,
          0.31,
          -0.25
        ]}
        rotation={[
          -0.4,
          0,
          0
        ]}
      >
        <boxGeometry
          args={[
            0.28,
            0.045,
            0.13
          ]}
        />

        <meshPhysicalMaterial
          color="#080b0d"
          roughness={0.12}
          metalness={0.2}
          transmission={0.15}
        />
      </mesh>

      <Panel
        position={[
          -0.34,
          0.95,
          0
        ]}
      />

      <Panel
        position={[
          -0.34,
          -0.95,
          0
        ]}
      />

      <mesh
        position={[
          -0.34,
          0.58,
          0
        ]}
      >
        <boxGeometry
          args={[
            0.08,
            0.76,
            0.08
          ]}
        />

        <meshStandardMaterial
          color="#7c8285"
          metalness={0.85}
          roughness={0.25}
        />
      </mesh>

      <mesh
        position={[
          -0.34,
          -0.58,
          0
        ]}
      >
        <boxGeometry
          args={[
            0.08,
            0.76,
            0.08
          ]}
        />

        <meshStandardMaterial
          color="#7c8285"
          metalness={0.85}
          roughness={0.25}
        />
      </mesh>

      <RcsThruster
        position={[
          0.25,
          0.48,
          0.25
        ]}
        active={rcsActive}
      />

      <RcsThruster
        position={[
          0.25,
          -0.48,
          -0.25
        ]}
        rotation={[
          0,
          0,
          Math.PI
        ]}
        active={rcsActive}
      />

      <pointLight
        position={[
          -0.95,
          0,
          0
        ]}
        color="#6ec8ff"
        intensity={1.2}
        distance={2}
      />

      {hovered && (
        <Html
          position={[
            0,
            1.55,
            0
          ]}
          center
          distanceFactor={7}
          style={{
            pointerEvents:
              "none"
          }}
        >
          <div className="cinematic-object-label">
            <span>
              ORION
            </span>

            <strong>
              CREW VEHICLE
            </strong>
          </div>
        </Html>
      )}
    </group>
  );
}

function DetailedGateway({
  cameraState,
  reducedMotion
}) {
  const root = useRef();
  const [hovered, setHovered] =
    useState(false);

  useFrame(
    (
      state,
      delta
    ) => {
      if (!root.current) {
        return;
      }

      const data =
        cameraState.current;

      if (!reducedMotion) {
        root.current.rotation.y +=
          delta * 0.012;
      }

      root.current.rotation.x =
        THREE.MathUtils.damp(
          root.current.rotation.x,
          0.12 +
            data.pitch *
              0.045,
          2,
          delta
        );

      root.current.rotation.z =
        THREE.MathUtils.damp(
          root.current.rotation.z,
          0.08 -
            data.yaw *
              0.025,
          2,
          delta
        );

      root.current.position.y =
        2.2 +
        (
          reducedMotion
            ? 0
            : Math.sin(
                state.clock
                  .elapsedTime *
                  0.24
              ) *
              0.035
        );

      const target =
        hovered
          ? 0.53
          : 0.48;

      const scale =
        THREE.MathUtils.damp(
          root.current.scale.x,
          target,
          5,
          delta
        );

      root.current.scale.setScalar(
        scale
      );
    }
  );

  const modules =
    useMemo(
      () => [
        {
          y: 0,
          radius: 0.25,
          length: 1.2,
          color: "#b9bec0"
        },
        {
          y: 1.02,
          radius: 0.32,
          length: 0.75,
          color: "#d6d7d3"
        },
        {
          y: -0.98,
          radius: 0.29,
          length: 0.68,
          color: "#73787b"
        }
      ],
      []
    );

  return (
    <group
      ref={root}
      position={[
        3.75,
        2.2,
        -6.8
      ]}
      rotation={[
        0.12,
        -0.28,
        0.08
      ]}
      scale={0.48}
      onPointerEnter={event => {
        event.stopPropagation();
        setHovered(true);
        document.body.style.cursor =
          "crosshair";
      }}
      onPointerLeave={() => {
        setHovered(false);
        document.body.style.cursor =
          "";
      }}
    >
      {modules.map(
        (
          module,
          index
        ) => (
          <mesh
            key={index}
            position={[
              0,
              module.y,
              0
            ]}
          >
            <cylinderGeometry
              args={[
                module.radius,
                module.radius,
                module.length,
                40
              ]}
            />

            <meshPhysicalMaterial
              color={
                module.color
              }
              roughness={0.27}
              metalness={0.72}
              clearcoat={0.15}
            />
          </mesh>
        )
      )}

      <mesh
        position={[
          0,
          1.62,
          0
        ]}
      >
        <torusGeometry
          args={[
            0.2,
            0.04,
            18,
            48
          ]}
        />

        <meshPhysicalMaterial
          color="#7e8589"
          roughness={0.22}
          metalness={0.88}
        />
      </mesh>

      <mesh
        position={[
          0,
          -1.52,
          0
        ]}
      >
        <torusGeometry
          args={[
            0.19,
            0.04,
            18,
            48
          ]}
        />

        <meshPhysicalMaterial
          color="#747b7e"
          roughness={0.22}
          metalness={0.88}
        />
      </mesh>

      <mesh
        rotation={[
          0,
          0,
          Math.PI / 2
        ]}
      >
        <cylinderGeometry
          args={[
            0.045,
            0.045,
            7.2,
            16
          ]}
        />

        <meshStandardMaterial
          color="#7b8185"
          roughness={0.25}
          metalness={0.86}
        />
      </mesh>

      <Panel
        position={[
          2.55,
          0,
          0
        ]}
        scale={[
          1.9,
          1,
          1.15
        ]}
      />

      <Panel
        position={[
          -2.55,
          0,
          0
        ]}
        scale={[
          1.9,
          1,
          1.15
        ]}
      />

      <mesh
        position={[
          0.48,
          0.4,
          0
        ]}
        rotation={[
          0,
          0,
          -0.5
        ]}
      >
        <cylinderGeometry
          args={[
            0.025,
            0.025,
            1.1,
            12
          ]}
        />

        <meshStandardMaterial
          color="#969b9d"
          metalness={0.9}
          roughness={0.2}
        />
      </mesh>

      <mesh
        position={[
          -0.48,
          -0.4,
          0
        ]}
        rotation={[
          0,
          0,
          -0.5
        ]}
      >
        <cylinderGeometry
          args={[
            0.025,
            0.025,
            1.1,
            12
          ]}
        />

        <meshStandardMaterial
          color="#969b9d"
          metalness={0.9}
          roughness={0.2}
        />
      </mesh>

      <pointLight
        position={[
          0,
          1.75,
          0
        ]}
        color="#dbeeff"
        intensity={0.65}
        distance={1.5}
      />

      {hovered && (
        <Html
          position={[
            0,
            2.35,
            0
          ]}
          center
          distanceFactor={8}
          style={{
            pointerEvents:
              "none"
          }}
        >
          <div className="cinematic-object-label">
            <span>
              GATEWAY
            </span>

            <strong>
              LUNAR ORBIT PLATFORM
            </strong>
          </div>
        </Html>
      )}
    </group>
  );
}

function Lander({
  cameraState,
  reducedMotion
}) {
  const root = useRef();
  const [hovered, setHovered] =
    useState(false);

  useFrame(
    (
      state,
      delta
    ) => {
      if (!root.current) {
        return;
      }

      const data =
        cameraState.current;

      root.current.rotation.y =
        THREE.MathUtils.damp(
          root.current.rotation.y,
          -0.45 +
            data.yaw * 0.05,
          2,
          delta
        );

      root.current.rotation.x =
        THREE.MathUtils.damp(
          root.current.rotation.x,
          0.05 +
            data.pitch * 0.035,
          2,
          delta
        );

      root.current.position.y =
        -1.25 +
        (
          reducedMotion
            ? 0
            : Math.sin(
                state.clock
                  .elapsedTime *
                  0.3
              ) *
              0.025
        );
    }
  );

  return (
    <group
      ref={root}
      position={[
        5.2,
        -1.25,
        -8.7
      ]}
      rotation={[
        0.05,
        -0.45,
        0
      ]}
      scale={0.32}
      onPointerEnter={event => {
        event.stopPropagation();
        setHovered(true);
        document.body.style.cursor =
          "crosshair";
      }}
      onPointerLeave={() => {
        setHovered(false);
        document.body.style.cursor =
          "";
      }}
    >
      <mesh
        position={[
          0,
          0.6,
          0
        ]}
      >
        <cylinderGeometry
          args={[
            0.62,
            0.72,
            1.2,
            40
          ]}
        />

        <meshPhysicalMaterial
          color="#d6d0bd"
          roughness={0.55}
          metalness={0.38}
        />
      </mesh>

      <mesh
        position={[
          0,
          -0.25,
          0
        ]}
      >
        <cylinderGeometry
          args={[
            0.72,
            0.92,
            0.55,
            40
          ]}
        />

        <meshPhysicalMaterial
          color="#9b7e52"
          roughness={0.58}
          metalness={0.5}
        />
      </mesh>

      {[
        [-0.65, -0.7, -0.65],
        [0.65, -0.7, -0.65],
        [-0.65, -0.7, 0.65],
        [0.65, -0.7, 0.65]
      ].map(
        (
          position,
          index
        ) => (
          <group
            key={index}
            position={
              position
            }
          >
            <mesh
              rotation={[
                0,
                0,
                index % 2 ===
                  0
                  ? -0.55
                  : 0.55
              ]}
            >
              <cylinderGeometry
                args={[
                  0.045,
                  0.045,
                  1.15,
                  12
                ]}
              />

              <meshStandardMaterial
                color="#707477"
                metalness={0.8}
                roughness={0.3}
              />
            </mesh>

            <mesh
              position={[
                0,
                -0.52,
                0
              ]}
              rotation={[
                Math.PI / 2,
                0,
                0
              ]}
            >
              <cylinderGeometry
                args={[
                  0.19,
                  0.19,
                  0.035,
                  24
                ]}
              />

              <meshStandardMaterial
                color="#4d5052"
                metalness={0.65}
                roughness={0.45}
              />
            </mesh>
          </group>
        )
      )}

      <mesh
        position={[
          0,
          1.45,
          0
        ]}
      >
        <cylinderGeometry
          args={[
            0.18,
            0.18,
            0.55,
            24
          ]}
        />

        <meshPhysicalMaterial
          color="#b9bdbe"
          roughness={0.28}
          metalness={0.7}
        />
      </mesh>

      {hovered && (
        <Html
          position={[
            0,
            2.25,
            0
          ]}
          center
          distanceFactor={8}
          style={{
            pointerEvents:
              "none"
          }}
        >
          <div className="cinematic-object-label">
            <span>
              LUNAR LANDER
            </span>

            <strong>
              SURFACE TRANSFER
            </strong>
          </div>
        </Html>
      )}
    </group>
  );
}

export default function CinematicSpacecraftDetail({
  cameraState,
  reducedMotion
}) {
  return (
    <>
      <DetailedOrion
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

      <DetailedGateway
        cameraState={
          cameraState
        }
        reducedMotion={
          reducedMotion
        }
      />

      <Lander
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
