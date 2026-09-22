import {
  Suspense,
  useEffect,
  useMemo,
  useRef
} from "react";

import {
  Canvas,
  useFrame,
  useThree
} from "@react-three/fiber";

import {
  Billboard,
  Float,
  Sparkles,
  Stars
} from "@react-three/drei";

import {
  Bloom,
  EffectComposer,
  Noise,
  Vignette
} from "@react-three/postprocessing";

import * as THREE from "three";

import { getQualityProfile } from "../lib/quality.js";

const TAU = Math.PI * 2;

function createSeededRandom(seed = 1) {
  let value = seed >>> 0;

  return () => {
    value += 0x6d2b79f5;

    let result = value;

    result = Math.imul(
      result ^ (result >>> 15),
      result | 1
    );

    result ^= result +
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

function Atmosphere({
  radius,
  color,
  opacity = 0.15,
  scale = 1.04
}) {
  return (
    <mesh scale={scale}>
      <sphereGeometry
        args={[radius, 64, 64]}
      />

      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        blending={THREE.AdditiveBlending}
        side={THREE.BackSide}
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
        args={[radius, 48, 48]}
      />

      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        blending={THREE.AdditiveBlending}
        side={THREE.BackSide}
        depthWrite={false}
      />
    </mesh>
  );
}

function Earth() {
  const group = useRef();
  const planet = useRef();
  const cloudLayer = useRef();

  const continents = useMemo(() => {
    const random = createSeededRandom(14321);

    return Array.from(
      { length: 190 },
      (_, index) => {
        const phi =
          Math.acos(
            2 * random() - 1
          );

        const theta =
          TAU * random();

        const radius = 3.225;

        const position = new THREE.Vector3(
          radius *
            Math.sin(phi) *
            Math.cos(theta),
          radius * Math.cos(phi),
          radius *
            Math.sin(phi) *
            Math.sin(theta)
        );

        const size =
          0.025 +
          random() * 0.07;

        return {
          id: index,
          position,
          size,
          intensity:
            0.15 + random() * 0.55
        };
      }
    );
  }, []);

  useFrame((state, delta) => {
    if (planet.current) {
      planet.current.rotation.y +=
        delta * 0.018;
    }

    if (cloudLayer.current) {
      cloudLayer.current.rotation.y +=
        delta * 0.024;
    }

    if (group.current) {
      group.current.position.y =
        -0.65 +
        Math.sin(
          state.clock.elapsedTime * 0.14
        ) *
          0.035;
    }
  });

  return (
    <group
      ref={group}
      position={[-4.85, -0.65, -8.2]}
      rotation={[0.08, 0, -0.25]}
    >
      <mesh ref={planet}>
        <sphereGeometry
          args={[3.2, 128, 128]}
        />

        <meshPhysicalMaterial
          color="#102d48"
          roughness={0.72}
          metalness={0.02}
          clearcoat={0.12}
          clearcoatRoughness={0.7}
        />

        {continents.map(point => (
          <mesh
            key={point.id}
            position={point.position}
            scale={point.size}
          >
            <sphereGeometry
              args={[1, 6, 6]}
            />

            <meshBasicMaterial
              color="#d6a95d"
              transparent
              opacity={point.intensity}
              blending={
                THREE.AdditiveBlending
              }
              depthWrite={false}
            />
          </mesh>
        ))}
      </mesh>

      <mesh
        ref={cloudLayer}
        scale={1.006}
      >
        <sphereGeometry
          args={[3.2, 96, 96]}
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

function MoonCrater({
  position,
  scale,
  rotation
}) {
  return (
    <mesh
      position={position}
      rotation={rotation}
      scale={scale}
    >
      <torusGeometry
        args={[0.13, 0.035, 10, 28]}
      />

      <meshStandardMaterial
        color="#5e5d5a"
        roughness={1}
        metalness={0}
      />
    </mesh>
  );
}

function Moon() {
  const group = useRef();
  const surface = useRef();

  const craters = useMemo(() => {
    const random = createSeededRandom(8821);

    return Array.from(
      { length: 38 },
      (_, index) => {
        const theta =
          random() * TAU;

        const phi =
          0.25 +
          random() * (Math.PI - 0.5);

        const radius = 1.565;

        const position = [
          radius *
            Math.sin(phi) *
            Math.cos(theta),
          radius * Math.cos(phi),
          radius *
            Math.sin(phi) *
            Math.sin(theta)
        ];

        const normal =
          new THREE.Vector3(
            ...position
          ).normalize();

        const quaternion =
          new THREE.Quaternion();

        quaternion.setFromUnitVectors(
          new THREE.Vector3(0, 0, 1),
          normal
        );

        const euler =
          new THREE.Euler().setFromQuaternion(
            quaternion
          );

        return {
          id: index,
          position,
          rotation: [
            euler.x,
            euler.y,
            euler.z
          ],
          scale:
            0.35 +
            random() * 1.2
        };
      }
    );
  }, []);

  useFrame((state, delta) => {
    if (surface.current) {
      surface.current.rotation.y +=
        delta * 0.004;
    }

    if (group.current) {
      group.current.position.y =
        0.65 +
        Math.sin(
          state.clock.elapsedTime * 0.1
        ) *
          0.025;
    }
  });

  return (
    <group
      ref={group}
      position={[5.15, 0.65, -10.5]}
    >
      <group ref={surface}>
        <mesh>
          <sphereGeometry
            args={[1.55, 128, 128]}
          />

          <meshPhysicalMaterial
            color="#8b8983"
            roughness={0.97}
            metalness={0}
          />
        </mesh>

        {craters.map(crater => (
          <MoonCrater
            key={crater.id}
            position={crater.position}
            rotation={crater.rotation}
            scale={crater.scale}
          />
        ))}
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

function Mars() {
  const group = useRef();

  useFrame((state, delta) => {
    if (!group.current) {
      return;
    }

    group.current.rotation.y +=
      delta * 0.006;

    group.current.position.y =
      3.25 +
      Math.sin(
        state.clock.elapsedTime * 0.08
      ) *
        0.025;
  });

  return (
    <group
      ref={group}
      position={[8.8, 3.25, -18]}
    >
      <mesh>
        <sphereGeometry
          args={[0.72, 72, 72]}
        />

        <meshPhysicalMaterial
          color="#8d3523"
          roughness={0.92}
          metalness={0}
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

function SolarFlare() {
  const flare = useRef();

  useFrame(state => {
    if (!flare.current) {
      return;
    }

    const pulse =
      1 +
      Math.sin(
        state.clock.elapsedTime * 0.9
      ) *
        0.08;

    flare.current.scale.setScalar(pulse);
  });

  return (
    <group
      position={[0.45, 2.15, -11]}
    >
      <Billboard>
        <mesh ref={flare}>
          <circleGeometry
            args={[0.22, 48]}
          />

          <meshBasicMaterial
            color="#fff4d6"
            transparent
            opacity={0.95}
            blending={
              THREE.AdditiveBlending
            }
            depthWrite={false}
          />
        </mesh>

        <mesh scale={4}>
          <circleGeometry
            args={[0.22, 48]}
          />

          <meshBasicMaterial
            color="#ffad5a"
            transparent
            opacity={0.06}
            blending={
              THREE.AdditiveBlending
            }
            depthWrite={false}
          />
        </mesh>

        <mesh
          scale={[12, 0.035, 1]}
        >
          <planeGeometry
            args={[1, 1]}
          />

          <meshBasicMaterial
            color="#ffd4a0"
            transparent
            opacity={0.11}
            blending={
              THREE.AdditiveBlending
            }
            depthWrite={false}
          />
        </mesh>
      </Billboard>

      <pointLight
        color="#ffd7a1"
        intensity={12}
        distance={28}
        decay={2}
      />
    </group>
  );
}

function OrbitalArc({
  radiusX,
  radiusY,
  z,
  rotation = 0,
  opacity = 0.14,
  color = "#6ebcff"
}) {
  const geometry = useMemo(() => {
    const curve =
      new THREE.EllipseCurve(
        0,
        0,
        radiusX,
        radiusY,
        0,
        TAU,
        false,
        rotation
      );

    const points = curve
      .getPoints(280)
      .map(
        point =>
          new THREE.Vector3(
            point.x,
            point.y,
            z
          )
      );

    return new THREE.BufferGeometry()
      .setFromPoints(points);
  }, [
    radiusX,
    radiusY,
    z,
    rotation
  ]);

  useEffect(
    () => () => geometry.dispose(),
    [geometry]
  );

  return (
    <line geometry={geometry}>
      <lineBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        blending={
          THREE.AdditiveBlending
        }
        depthWrite={false}
      />
    </line>
  );
}

function Orion() {
  const group = useRef();

  useFrame((state, delta) => {
    if (!group.current) {
      return;
    }

    group.current.rotation.y +=
      delta * 0.12;

    group.current.rotation.z =
      -0.15 +
      Math.sin(
        state.clock.elapsedTime * 0.35
      ) *
        0.04;
  });

  return (
    <Float
      speed={1.1}
      rotationIntensity={0.08}
      floatIntensity={0.12}
    >
      <group
        ref={group}
        position={[2.3, -0.05, -4.2]}
        rotation={[0.05, -0.65, -0.15]}
        scale={0.72}
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
              0.36,
              0.58,
              0.72,
              48
            ]}
          />

          <meshPhysicalMaterial
            color="#d4d7d8"
            metalness={0.68}
            roughness={0.24}
            clearcoat={0.35}
          />
        </mesh>

        <mesh
          position={[0.52, 0, 0]}
          rotation={[
            0,
            0,
            -Math.PI / 2
          ]}
        >
          <coneGeometry
            args={[0.37, 0.42, 48]}
          />

          <meshPhysicalMaterial
            color="#22272d"
            metalness={0.82}
            roughness={0.18}
          />
        </mesh>

        <mesh
          position={[-0.55, 0, 0]}
          rotation={[
            0,
            0,
            Math.PI / 2
          ]}
        >
          <cylinderGeometry
            args={[
              0.28,
              0.32,
              0.4,
              32
            ]}
          />

          <meshStandardMaterial
            color="#161b20"
            metalness={0.72}
            roughness={0.3}
          />
        </mesh>

        <mesh
          position={[0, 0.72, 0]}
        >
          <boxGeometry
            args={[1.75, 0.035, 0.48]}
          />

          <meshPhysicalMaterial
            color="#102b54"
            metalness={0.45}
            roughness={0.36}
          />
        </mesh>

        <mesh
          position={[0, -0.72, 0]}
        >
          <boxGeometry
            args={[1.75, 0.035, 0.48]}
          />

          <meshPhysicalMaterial
            color="#102b54"
            metalness={0.45}
            roughness={0.36}
          />
        </mesh>

        <pointLight
          position={[-0.8, 0, 0]}
          color="#4ca8ff"
          intensity={2}
          distance={2}
        />
      </group>
    </Float>
  );
}

function Gateway() {
  const group = useRef();

  useFrame((state, delta) => {
    if (!group.current) {
      return;
    }

    group.current.rotation.y +=
      delta * 0.018;

    group.current.rotation.x =
      0.16 +
      Math.sin(
        state.clock.elapsedTime * 0.17
      ) *
        0.025;
  });

  return (
    <Float
      speed={0.7}
      rotationIntensity={0.04}
      floatIntensity={0.1}
    >
      <group
        ref={group}
        position={[3.6, 2.25, -7]}
        rotation={[0.16, -0.3, 0.1]}
        scale={0.48}
      >
        <mesh>
          <cylinderGeometry
            args={[
              0.25,
              0.25,
              2.2,
              28
            ]}
          />

          <meshPhysicalMaterial
            color="#bfc4c8"
            metalness={0.72}
            roughness={0.25}
          />
        </mesh>

        <mesh
          position={[0, 1.35, 0]}
        >
          <cylinderGeometry
            args={[
              0.38,
              0.38,
              0.65,
              28
            ]}
          />

          <meshPhysicalMaterial
            color="#d7d9d8"
            metalness={0.62}
            roughness={0.28}
          />
        </mesh>

        <mesh
          position={[0, -1.3, 0]}
        >
          <cylinderGeometry
            args={[
              0.32,
              0.32,
              0.55,
              28
            ]}
          />

          <meshPhysicalMaterial
            color="#6d7278"
            metalness={0.78}
            roughness={0.24}
          />
        </mesh>

        <mesh
          position={[1.8, 0.35, 0]}
        >
          <boxGeometry
            args={[3.1, 0.055, 0.82]}
          />

          <meshPhysicalMaterial
            color="#182d49"
            metalness={0.42}
            roughness={0.4}
          />
        </mesh>

        <mesh
          position={[-1.8, 0.35, 0]}
        >
          <boxGeometry
            args={[3.1, 0.055, 0.82]}
          />

          <meshPhysicalMaterial
            color="#182d49"
            metalness={0.42}
            roughness={0.4}
          />
        </mesh>

        <mesh
          position={[0, 0.3, 0]}
          rotation={[
            0,
            0,
            Math.PI / 2
          ]}
        >
          <cylinderGeometry
            args={[
              0.08,
              0.08,
              4,
              16
            ]}
          />

          <meshStandardMaterial
            color="#72777d"
            metalness={0.8}
            roughness={0.25}
          />
        </mesh>
      </group>
    </Float>
  );
}

function LaunchStack() {
  const group = useRef();

  useFrame(state => {
    if (!group.current) {
      return;
    }

    group.current.position.y =
      -2.55 +
      Math.sin(
        state.clock.elapsedTime * 0.2
      ) *
        0.015;
  });

  return (
    <group
      ref={group}
      position={[-0.35, -2.55, -6.5]}
      scale={0.58}
    >
      <mesh
        position={[0, 2.3, 0]}
      >
        <cylinderGeometry
          args={[
            0.34,
            0.34,
            4.5,
            36
          ]}
        />

        <meshPhysicalMaterial
          color="#d86d25"
          roughness={0.48}
          metalness={0.08}
        />
      </mesh>

      <mesh
        position={[0, 4.8, 0]}
      >
        <coneGeometry
          args={[0.34, 0.85, 36]}
        />

        <meshPhysicalMaterial
          color="#ecebe7"
          roughness={0.38}
          metalness={0.12}
        />
      </mesh>

      <mesh
        position={[-0.58, 1.85, 0]}
      >
        <cylinderGeometry
          args={[
            0.16,
            0.16,
            3.8,
            24
          ]}
        />

        <meshStandardMaterial
          color="#e5e6e2"
          roughness={0.55}
        />
      </mesh>

      <mesh
        position={[0.58, 1.85, 0]}
      >
        <cylinderGeometry
          args={[
            0.16,
            0.16,
            3.8,
            24
          ]}
        />

        <meshStandardMaterial
          color="#e5e6e2"
          roughness={0.55}
        />
      </mesh>

      <pointLight
        position={[0, -0.2, 0]}
        color="#ff7b30"
        intensity={5}
        distance={4}
      />
    </group>
  );
}

function DeepSpaceDust({ quality }) {
  const count =
    quality.tier === "high"
      ? 320
      : quality.tier === "medium"
        ? 170
        : 70;

  return (
    <>
      <Sparkles
        count={count}
        scale={[24, 14, 28]}
        size={
          quality.tier === "high"
            ? 1.6
            : 1.1
        }
        speed={0.12}
        opacity={0.25}
        color="#b9d9ff"
        noise={1.3}
      />

      <Sparkles
        count={Math.floor(count * 0.35)}
        scale={[18, 10, 22]}
        size={2.2}
        speed={0.05}
        opacity={0.11}
        color="#f4d3a2"
        noise={2}
      />
    </>
  );
}

function CameraRig({
  progress,
  pointer,
  reducedMotion
}) {
  const { camera } = useThree();

  const target = useMemo(
    () => new THREE.Vector3(),
    []
  );

  useFrame(state => {
    const p = progress.current;

    const scrollCurve =
      p * p * (3 - 2 * p);

    const pointerX =
      reducedMotion
        ? 0
        : pointer.current.x;

    const pointerY =
      reducedMotion
        ? 0
        : pointer.current.y;

    const desiredX =
      THREE.MathUtils.lerp(
        0,
        2.7,
        scrollCurve
      ) +
      pointerX * 0.32;

    const desiredY =
      THREE.MathUtils.lerp(
        0.05,
        -0.65,
        scrollCurve
      ) +
      pointerY * 0.2;

    const desiredZ =
      THREE.MathUtils.lerp(
        7.4,
        9.8,
        scrollCurve
      );

    camera.position.x =
      THREE.MathUtils.damp(
        camera.position.x,
        desiredX,
        3.4,
        state.clock.getDelta()
      );

    camera.position.y =
      THREE.MathUtils.damp(
        camera.position.y,
        desiredY,
        3.4,
        1 / 60
      );

    camera.position.z =
      THREE.MathUtils.damp(
        camera.position.z,
        desiredZ,
        3.4,
        1 / 60
      );

    target.set(
      THREE.MathUtils.lerp(
        -0.25,
        1.1,
        scrollCurve
      ),
      THREE.MathUtils.lerp(
        0,
        -0.15,
        scrollCurve
      ),
      THREE.MathUtils.lerp(
        -5,
        -7.3,
        scrollCurve
      )
    );

    camera.lookAt(target);
  });

  return null;
}

function CinematicLighting() {
  return (
    <>
      <ambientLight
        intensity={0.035}
      />

      <hemisphereLight
        args={[
          "#89baff",
          "#080706",
          0.12
        ]}
      />

      <directionalLight
        position={[4.5, 5, 3]}
        intensity={3.8}
        color="#fff3da"
      />

      <directionalLight
        position={[-8, 1, -2]}
        intensity={1.25}
        color="#2879ff"
      />

      <pointLight
        position={[6, -2, -2]}
        intensity={1.4}
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
    quality.tier === "low"
  ) {
    return null;
  }

  return (
    <EffectComposer
      multisampling={
        quality.tier === "high"
          ? 4
          : 0
      }
    >
      <Bloom
        intensity={
          reducedMotion
            ? 0.45
            : 0.75
        }
        luminanceThreshold={0.72}
        luminanceSmoothing={0.22}
        mipmapBlur
      />

      <Noise
        opacity={0.012}
        premultiply
      />

      <Vignette
        eskil={false}
        offset={0.18}
        darkness={0.72}
      />
    </EffectComposer>
  );
}

function Scene({
  progress,
  pointer,
  quality,
  reducedMotion
}) {
  return (
    <>
      <color
        attach="background"
        args={["#010205"]}
      />

      <fogExp2
        attach="fog"
        args={["#02050a", 0.012]}
      />

      <CinematicLighting />

      <Stars
        radius={110}
        depth={75}
        count={quality.stars}
        factor={2.6}
        saturation={0.08}
        fade
        speed={
          reducedMotion
            ? 0
            : 0.035
        }
      />

      <DeepSpaceDust
        quality={quality}
      />

      <SolarFlare />

      <Earth />
      <Moon />
      <Mars />

      <OrbitalArc
        radiusX={7.2}
        radiusY={2.7}
        z={-5.5}
        rotation={0.2}
        opacity={0.13}
      />

      <OrbitalArc
        radiusX={4.2}
        radiusY={1.5}
        z={-7.2}
        rotation={-0.4}
        opacity={0.09}
        color="#ffffff"
      />

      <OrbitalArc
        radiusX={9.6}
        radiusY={3.7}
        z={-11}
        rotation={0.5}
        opacity={0.055}
        color="#ffb67c"
      />

      <LaunchStack />
      <Orion />
      <Gateway />

      <CameraRig
        progress={progress}
        pointer={pointer}
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

export default function SpaceScene() {
  const progress = useRef(0);

  const pointer = useRef({
    x: 0,
    y: 0
  });

  const quality = useMemo(
    () => getQualityProfile(),
    []
  );

  const reducedMotion =
    useMemo(
      () =>
        window.matchMedia(
          "(prefers-reduced-motion: reduce)"
        ).matches,
      []
    );

  useEffect(() => {
    function updateScroll() {
      const documentHeight =
        document.documentElement
          .scrollHeight -
        window.innerHeight;

      progress.current =
        documentHeight > 0
          ? Math.min(
              1,
              Math.max(
                0,
                window.scrollY /
                  documentHeight
              )
            )
          : 0;
    }

    function updatePointer(event) {
      pointer.current.x =
        (event.clientX /
          window.innerWidth) *
          2 -
        1;

      pointer.current.y =
        -(
          (event.clientY /
            window.innerHeight) *
            2 -
          1
        );
    }

    function resetPointer() {
      pointer.current.x = 0;
      pointer.current.y = 0;
    }

    updateScroll();

    window.addEventListener(
      "scroll",
      updateScroll,
      { passive: true }
    );

    if (!reducedMotion) {
      window.addEventListener(
        "pointermove",
        updatePointer,
        { passive: true }
      );

      window.addEventListener(
        "pointerleave",
        resetPointer
      );
    }

    return () => {
      window.removeEventListener(
        "scroll",
        updateScroll
      );

      window.removeEventListener(
        "pointermove",
        updatePointer
      );

      window.removeEventListener(
        "pointerleave",
        resetPointer
      );
    };
  }, [reducedMotion]);

  return (
    <div
      className="space-canvas"
      aria-hidden="true"
    >
      <Canvas
        dpr={quality.dpr}
        camera={{
          position: [0, 0, 7.4],
          fov: 41,
          near: 0.08,
          far: 240
        }}
        gl={{
          antialias:
            quality.tier !== "low",
          alpha: false,
          powerPreference:
            "high-performance",
          toneMapping:
            THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.08
        }}
        onCreated={({ gl }) => {
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
        <Suspense fallback={null}>
          <Scene
            progress={progress}
            pointer={pointer}
            quality={quality}
            reducedMotion={
              reducedMotion
            }
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
