import {
  Suspense,
  useEffect,
  useMemo,
  useRef
} from "react";

import { Canvas, useFrame, useThree } from "@react-three/fiber";

import {
  Stars
} from "@react-three/drei";

import * as THREE from "three";

import { getQualityProfile } from "../lib/quality.js";

function Earth() {
  const group = useRef();
  const surface = useRef();

  useFrame((state, delta) => {
    if (surface.current) {
      surface.current.rotation.y += delta * 0.025;
    }

    if (group.current) {
      group.current.position.y =
        Math.sin(state.clock.elapsedTime * 0.18) * 0.05;
    }
  });

  return (
    <group
      ref={group}
      position={[-4.8, -0.7, -7]}
      rotation={[0.1, 0, -0.22]}
    >
      <mesh ref={surface}>
        <sphereGeometry args={[3.2, 96, 96]} />

        <meshStandardMaterial
          color="#17324a"
          roughness={0.78}
          metalness={0.03}
        />
      </mesh>

      <mesh scale={1.018}>
        <sphereGeometry args={[3.2, 96, 96]} />

        <meshBasicMaterial
          color="#4ba3d8"
          transparent
          opacity={0.08}
          side={THREE.BackSide}
        />
      </mesh>

      <mesh scale={1.06}>
        <sphereGeometry args={[3.2, 64, 64]} />

        <meshBasicMaterial
          color="#5cbcff"
          transparent
          opacity={0.035}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}

function Moon() {
  const moon = useRef();

  useFrame((state, delta) => {
    if (moon.current) {
      moon.current.rotation.y += delta * 0.008;

      moon.current.position.y =
        0.5 +
        Math.sin(state.clock.elapsedTime * 0.13) * 0.035;
    }
  });

  return (
    <group
      ref={moon}
      position={[5.2, 0.5, -10]}
    >
      <mesh>
        <sphereGeometry args={[1.55, 96, 96]} />

        <meshStandardMaterial
          color="#aaa79f"
          roughness={1}
          metalness={0}
        />
      </mesh>

      <mesh
        position={[-0.45, 0.45, 1.44]}
        rotation={[0, 0, 0]}
      >
        <circleGeometry args={[0.16, 32]} />

        <meshBasicMaterial
          color="#77756f"
          transparent
          opacity={0.28}
        />
      </mesh>

      <mesh
        position={[0.38, -0.25, 1.47]}
      >
        <circleGeometry args={[0.22, 32]} />

        <meshBasicMaterial
          color="#706e68"
          transparent
          opacity={0.22}
        />
      </mesh>
    </group>
  );
}

function OrbitLine() {
  const geometry = useMemo(() => {
    const curve = new THREE.EllipseCurve(
      0,
      0,
      6.8,
      2.5,
      0,
      Math.PI * 2,
      false,
      0.25
    );

    const points = curve
      .getPoints(220)
      .map(
        point =>
          new THREE.Vector3(
            point.x,
            point.y,
            -5
          )
      );

    return new THREE.BufferGeometry().setFromPoints(points);
  }, []);

  return (
    <line geometry={geometry}>
      <lineBasicMaterial
        color="#ffffff"
        transparent
        opacity={0.12}
      />
    </line>
  );
}

function Vehicle() {
  const vehicle = useRef();

  useFrame(state => {
    if (!vehicle.current) return;

    const time = state.clock.elapsedTime * 0.07;

    vehicle.current.position.x =
      Math.cos(time) * 6.8;

    vehicle.current.position.y =
      Math.sin(time) * 2.5;

    vehicle.current.position.z = -5;

    vehicle.current.rotation.z =
      time + Math.PI / 2;
  });

  return (
    <group ref={vehicle}>
      <mesh rotation={[0, 0, Math.PI / 2]}>
        <coneGeometry args={[0.08, 0.3, 12]} />

        <meshBasicMaterial color="#ffffff" />
      </mesh>

      <pointLight
        color="#ffffff"
        intensity={1.5}
        distance={1.2}
      />
    </group>
  );
}

function CameraRig({ progress }) {
  const { camera } = useThree();

  useFrame(() => {
    const p = progress.current;

    const targetX = THREE.MathUtils.lerp(
      0,
      2.3,
      p
    );

    const targetY = THREE.MathUtils.lerp(
      0,
      -0.5,
      p
    );

    const targetZ = THREE.MathUtils.lerp(
      7,
      9,
      p
    );

    camera.position.x = THREE.MathUtils.lerp(
      camera.position.x,
      targetX,
      0.025
    );

    camera.position.y = THREE.MathUtils.lerp(
      camera.position.y,
      targetY,
      0.025
    );

    camera.position.z = THREE.MathUtils.lerp(
      camera.position.z,
      targetZ,
      0.025
    );

    camera.lookAt(0, 0, -4);
  });

  return null;
}

function Scene({ progress, quality }) {
  return (
    <>
      <color attach="background" args={["#030507"]} />

      <ambientLight intensity={0.08} />

      <directionalLight
        position={[7, 4, 5]}
        intensity={2.7}
        color="#fff8ea"
      />

      <pointLight
        position={[-6, -2, -2]}
        intensity={0.8}
        color="#4f91ba"
      />

      <Stars
        radius={85}
        depth={55}
        count={quality.stars}
        factor={2.2}
        saturation={0}
        fade
        speed={0.08}
      />

      <Earth />
      <Moon />
      <OrbitLine />
      <Vehicle />
      <CameraRig progress={progress} />
    </>
  );
}

export default function SpaceScene() {
  const progress = useRef(0);

  const quality = useMemo(
    () => getQualityProfile(),
    []
  );

  useEffect(() => {
    function update() {
      const documentHeight =
        document.documentElement.scrollHeight -
        window.innerHeight;

      progress.current =
        documentHeight > 0
          ? Math.min(
              1,
              window.scrollY / documentHeight
            )
          : 0;
    }

    update();

    window.addEventListener(
      "scroll",
      update,
      { passive: true }
    );

    return () =>
      window.removeEventListener(
        "scroll",
        update
      );
  }, []);

  return (
    <div className="space-canvas" aria-hidden="true">
      <Canvas
        dpr={quality.dpr}
        camera={{
          position: [0, 0, 7],
          fov: 42,
          near: 0.1,
          far: 200
        }}
        gl={{
          antialias: quality.tier !== "low",
          alpha: false,
          powerPreference: "high-performance"
        }}
      >
        <Suspense fallback={null}>
          <Scene
            progress={progress}
            quality={quality}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
