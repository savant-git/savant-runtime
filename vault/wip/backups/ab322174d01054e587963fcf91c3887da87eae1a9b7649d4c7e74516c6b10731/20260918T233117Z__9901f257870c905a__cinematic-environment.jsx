import {
  useEffect,
  useMemo,
  useRef
} from "react";

import {
  Billboard,
  Sparkles
} from "@react-three/drei";

import {
  useFrame,
  useThree
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

function createStarField(
  count,
  radius,
  depth,
  seed
) {
  const random = seededRandom(seed);

  const positions =
    new Float32Array(count * 3);

  const colors =
    new Float32Array(count * 3);

  const sizes =
    new Float32Array(count);

  const warm = new THREE.Color(
    "#ffd8b0"
  );

  const neutral = new THREE.Color(
    "#eef5ff"
  );

  const cool = new THREE.Color(
    "#9fcaff"
  );

  for (
    let index = 0;
    index < count;
    index += 1
  ) {
    const offset = index * 3;

    const theta = random() * TAU;

    const phi =
      Math.acos(
        THREE.MathUtils.clamp(
          2 * random() - 1,
          -1,
          1
        )
      );

    const distance =
      radius +
      random() * depth;

    positions[offset] =
      Math.sin(phi) *
      Math.cos(theta) *
      distance;

    positions[offset + 1] =
      Math.cos(phi) * distance;

    positions[offset + 2] =
      Math.sin(phi) *
      Math.sin(theta) *
      distance;

    const temperature = random();

    const color =
      temperature < 0.12
        ? warm
        : temperature > 0.78
          ? cool
          : neutral;

    const intensity =
      0.55 + random() * 0.45;

    colors[offset] =
      color.r * intensity;

    colors[offset + 1] =
      color.g * intensity;

    colors[offset + 2] =
      color.b * intensity;

    sizes[index] =
      0.5 +
      Math.pow(random(), 5) * 2.5;
  }

  return {
    positions,
    colors,
    sizes
  };
}

function StarLayer({
  count,
  radius,
  depth,
  seed,
  size,
  opacity,
  parallax,
  cameraState
}) {
  const points = useRef();

  const field = useMemo(
    () =>
      createStarField(
        count,
        radius,
        depth,
        seed
      ),
    [
      count,
      radius,
      depth,
      seed
    ]
  );

  useFrame((state, delta) => {
    if (!points.current) {
      return;
    }

    const targetX =
      -cameraState.current.yaw *
      parallax;

    const targetY =
      cameraState.current.pitch *
      parallax;

    points.current.rotation.y =
      THREE.MathUtils.damp(
        points.current.rotation.y,
        targetX,
        2.2,
        delta
      );

    points.current.rotation.x =
      THREE.MathUtils.damp(
        points.current.rotation.x,
        targetY,
        2.2,
        delta
      );

    points.current.position.x =
      THREE.MathUtils.damp(
        points.current.position.x,
        -cameraState.current.positionX *
          parallax *
          0.08,
        2,
        delta
      );

    points.current.position.y =
      THREE.MathUtils.damp(
        points.current.position.y,
        -cameraState.current.positionY *
          parallax *
          0.08,
        2,
        delta
      );

    points.current.rotation.z +=
      delta * 0.00012;
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[
            field.positions,
            3
          ]}
        />

        <bufferAttribute
          attach="attributes-color"
          args={[
            field.colors,
            3
          ]}
        />
      </bufferGeometry>

      <pointsMaterial
        size={size}
        vertexColors
        transparent
        opacity={opacity}
        sizeAttenuation
        depthWrite={false}
        blending={
          THREE.AdditiveBlending
        }
        toneMapped={false}
      />
    </points>
  );
}

function MatteEnvironment({
  cameraState,
  reducedMotion
}) {
  const layer = useRef();

  const texture = useMemo(() => {
    const loaded =
      new THREE.TextureLoader().load(
        "/assets/artemis-deep-space-matte.webp"
      );

    loaded.colorSpace =
      THREE.SRGBColorSpace;

    loaded.minFilter =
      THREE.LinearMipmapLinearFilter;

    loaded.magFilter =
      THREE.LinearFilter;

    loaded.generateMipmaps = true;

    loaded.wrapS =
      THREE.ClampToEdgeWrapping;

    loaded.wrapT =
      THREE.ClampToEdgeWrapping;

    return loaded;
  }, []);

  useEffect(
    () => () => texture.dispose(),
    [texture]
  );

  useFrame((state, delta) => {
    if (!layer.current) {
      return;
    }

    const yaw =
      reducedMotion
        ? 0
        : cameraState.current.yaw;

    const pitch =
      reducedMotion
        ? 0
        : cameraState.current.pitch;

    /*
     * The plane is deliberately much larger
     * than the default frustum. The central
     * region is therefore the authored
     * default composition while camera motion
     * reveals overscan instead of exposing
     * an image edge.
     */
    const targetX = yaw * -3.2;
    const targetY = pitch * 2.15;

    layer.current.position.x =
      THREE.MathUtils.damp(
        layer.current.position.x,
        targetX,
        1.7,
        delta
      );

    layer.current.position.y =
      THREE.MathUtils.damp(
        layer.current.position.y,
        targetY,
        1.7,
        delta
      );

    layer.current.rotation.y =
      THREE.MathUtils.damp(
        layer.current.rotation.y,
        yaw * -0.012,
        1.6,
        delta
      );

    layer.current.rotation.x =
      THREE.MathUtils.damp(
        layer.current.rotation.x,
        pitch * 0.009,
        1.6,
        delta
      );
  });

  return (
    <mesh
      ref={layer}
      position={[0, 0, -72]}
      scale={[1.34, 1.34, 1]}
      frustumCulled={false}
      renderOrder={-100}
    >
      <planeGeometry
        args={[142, 80]}
      />

      <meshBasicMaterial
        map={texture}
        color="#d6dbe1"
        fog={false}
        depthWrite={false}
        depthTest={false}
        toneMapped
      />
    </mesh>
  );
}

function NearDust({
  quality,
  cameraState,
  reducedMotion
}) {
  const group = useRef();

  const count =
    quality.tier === "high"
      ? 260
      : quality.tier === "medium"
        ? 140
        : 60;

  useFrame((state, delta) => {
    if (!group.current) {
      return;
    }

    const drift =
      reducedMotion
        ? 0
        : state.clock.elapsedTime;

    group.current.position.x =
      THREE.MathUtils.damp(
        group.current.position.x,
        -cameraState.current.yaw *
          0.7,
        2.4,
        delta
      );

    group.current.position.y =
      THREE.MathUtils.damp(
        group.current.position.y,
        cameraState.current.pitch *
          0.48,
        2.4,
        delta
      );

    if (!reducedMotion) {
      group.current.rotation.z =
        Math.sin(drift * 0.04) *
        0.015;
    }
  });

  return (
    <group ref={group}>
      <Sparkles
        count={count}
        scale={[22, 12, 20]}
        size={
          quality.tier === "high"
            ? 1.75
            : 1.25
        }
        speed={
          reducedMotion
            ? 0
            : 0.055
        }
        opacity={0.14}
        color="#c8d8e8"
        noise={1.6}
      />

      <Sparkles
        count={Math.floor(
          count * 0.24
        )}
        scale={[17, 9, 16]}
        size={2.1}
        speed={
          reducedMotion
            ? 0
            : 0.025
        }
        opacity={0.075}
        color="#e7c69d"
        noise={2.2}
      />
    </group>
  );
}

function OpticalFlare({
  cameraState,
  reducedMotion
}) {
  const group = useRef();

  useFrame((state, delta) => {
    if (!group.current) {
      return;
    }

    const yaw =
      cameraState.current.yaw;

    const pitch =
      cameraState.current.pitch;

    const visibility =
      THREE.MathUtils.clamp(
        1 -
          Math.abs(yaw + 0.18) *
            1.8 -
          Math.abs(pitch - 0.03) *
            1.4,
        0,
        1
      );

    group.current.visible =
      visibility > 0.015;

    const pulse =
      reducedMotion
        ? 1
        : 1 +
          Math.sin(
            state.clock.elapsedTime *
              0.75
          ) *
            0.035;

    group.current.scale.setScalar(
      THREE.MathUtils.damp(
        group.current.scale.x,
        pulse,
        2,
        delta
      )
    );

    group.current.children.forEach(
      child => {
        if (
          child.material &&
          "opacity" in child.material
        ) {
          const base =
            child.userData.baseOpacity ??
            0.1;

          child.material.opacity =
            base * visibility;
        }
      }
    );
  });

  return (
    <group
      ref={group}
      position={[-0.65, 2.35, -12]}
    >
      <Billboard>
        <mesh
          userData={{
            baseOpacity: 0.75
          }}
        >
          <circleGeometry
            args={[0.13, 48]}
          />

          <meshBasicMaterial
            color="#fff7e8"
            transparent
            opacity={0.75}
            depthWrite={false}
            toneMapped={false}
            blending={
              THREE.AdditiveBlending
            }
          />
        </mesh>

        <mesh
          scale={5.5}
          userData={{
            baseOpacity: 0.075
          }}
        >
          <circleGeometry
            args={[0.18, 48]}
          />

          <meshBasicMaterial
            color="#ffbd79"
            transparent
            opacity={0.075}
            depthWrite={false}
            toneMapped={false}
            blending={
              THREE.AdditiveBlending
            }
          />
        </mesh>

        <mesh
          scale={[18, 0.025, 1]}
          userData={{
            baseOpacity: 0.095
          }}
        >
          <planeGeometry
            args={[1, 1]}
          />

          <meshBasicMaterial
            color="#ffd6a4"
            transparent
            opacity={0.095}
            depthWrite={false}
            toneMapped={false}
            blending={
              THREE.AdditiveBlending
            }
          />
        </mesh>

        <mesh
          position={[1.25, -0.28, 0]}
          scale={0.38}
          userData={{
            baseOpacity: 0.055
          }}
        >
          <circleGeometry
            args={[0.28, 32]}
          />

          <meshBasicMaterial
            color="#8cb8d7"
            transparent
            opacity={0.055}
            depthWrite={false}
            toneMapped={false}
            blending={
              THREE.AdditiveBlending
            }
          />
        </mesh>

        <mesh
          position={[2.1, -0.46, 0]}
          scale={0.2}
          userData={{
            baseOpacity: 0.04
          }}
        >
          <circleGeometry
            args={[0.32, 32]}
          />

          <meshBasicMaterial
            color="#df9e6b"
            transparent
            opacity={0.04}
            depthWrite={false}
            toneMapped={false}
            blending={
              THREE.AdditiveBlending
            }
          />
        </mesh>
      </Billboard>
    </group>
  );
}

export function createCameraState() {
  return {
    yaw: 0,
    pitch: 0,
    targetYaw: 0,
    targetPitch: 0,
    yawVelocity: 0,
    pitchVelocity: 0,
    positionX: 0,
    positionY: 0,
    dragging: false,
    lastX: 0,
    lastY: 0,
    pointerId: null,
    impulse: 0,
    scroll: 0
  };
}

export function CinematicCameraRig({
  cameraState,
  progress,
  reducedMotion
}) {
  const { camera } = useThree();

  const lookTarget = useMemo(
    () => new THREE.Vector3(),
    []
  );

  const desiredPosition =
    useMemo(
      () => new THREE.Vector3(),
      []
    );

  useFrame((state, delta) => {
    const frameDelta =
      Math.min(delta, 1 / 20);

    const data = cameraState.current;

    const scroll =
      progress?.current ?? 0;

    data.scroll = scroll;

    if (!reducedMotion) {
      if (!data.dragging) {
        data.targetYaw +=
          data.yawVelocity *
          frameDelta;

        data.targetPitch +=
          data.pitchVelocity *
          frameDelta;

        const inertia =
          Math.pow(
            0.055,
            frameDelta
          );

        data.yawVelocity *= inertia;
        data.pitchVelocity *= inertia;
      }

      data.targetYaw =
        THREE.MathUtils.clamp(
          data.targetYaw,
          -0.72,
          0.72
        );

      data.targetPitch =
        THREE.MathUtils.clamp(
          data.targetPitch,
          -0.38,
          0.38
        );
    } else {
      data.targetYaw = 0;
      data.targetPitch = 0;
      data.yawVelocity = 0;
      data.pitchVelocity = 0;
    }

    data.yaw =
      THREE.MathUtils.damp(
        data.yaw,
        data.targetYaw,
        data.dragging ? 13 : 5.5,
        frameDelta
      );

    data.pitch =
      THREE.MathUtils.damp(
        data.pitch,
        data.targetPitch,
        data.dragging ? 13 : 5.5,
        frameDelta
      );

    const easedScroll =
      scroll *
      scroll *
      (3 - 2 * scroll);

    const drift =
      reducedMotion
        ? 0
        : Math.sin(
            state.clock.elapsedTime *
              0.21
          ) *
          0.008;

    const microShake =
      reducedMotion
        ? 0
        : (
            Math.sin(
              state.clock.elapsedTime *
                2.7
            ) *
              0.0014 +
            Math.sin(
              state.clock.elapsedTime *
                5.13
            ) *
              0.00065
          ) *
          (0.35 +
            Math.abs(
              data.yawVelocity
            ) *
              0.025);

    data.positionX =
      data.yaw * 1.25;

    data.positionY =
      data.pitch * 0.82;

    desiredPosition.set(
      THREE.MathUtils.lerp(
        0,
        2.4,
        easedScroll
      ) +
        data.positionX +
        microShake,
      THREE.MathUtils.lerp(
        0.08,
        -0.55,
        easedScroll
      ) +
        data.positionY +
        drift,
      THREE.MathUtils.lerp(
        7.4,
        9.4,
        easedScroll
      )
    );

    camera.position.x =
      THREE.MathUtils.damp(
        camera.position.x,
        desiredPosition.x,
        4.8,
        frameDelta
      );

    camera.position.y =
      THREE.MathUtils.damp(
        camera.position.y,
        desiredPosition.y,
        4.8,
        frameDelta
      );

    camera.position.z =
      THREE.MathUtils.damp(
        camera.position.z,
        desiredPosition.z,
        4.8,
        frameDelta
      );

    lookTarget.set(
      THREE.MathUtils.lerp(
        -0.15,
        1.05,
        easedScroll
      ) +
        Math.sin(data.yaw) *
          4.4,
      THREE.MathUtils.lerp(
        0,
        -0.1,
        easedScroll
      ) +
        Math.sin(data.pitch) *
          3.2,
      THREE.MathUtils.lerp(
        -5.2,
        -7.2,
        easedScroll
      )
    );

    camera.lookAt(lookTarget);

    const motion =
      Math.min(
        1,
        Math.abs(
          data.yawVelocity
        ) *
          0.025 +
          Math.abs(
            data.pitchVelocity
          ) *
            0.025
      );

    const targetFov =
      41 +
      motion * 3.2 +
      Math.abs(data.yaw) * 1.8;

    camera.fov =
      THREE.MathUtils.damp(
        camera.fov,
        targetFov,
        4,
        frameDelta
      );

    camera.updateProjectionMatrix();
  });

  return null;
}

export function CinematicEnvironment({
  quality,
  cameraState,
  reducedMotion
}) {
  const farCount =
    quality.tier === "high"
      ? 2800
      : quality.tier === "medium"
        ? 1500
        : 650;

  const middleCount =
    quality.tier === "high"
      ? 1250
      : quality.tier === "medium"
        ? 700
        : 280;

  const nearCount =
    quality.tier === "high"
      ? 480
      : quality.tier === "medium"
        ? 260
        : 100;

  return (
    <>
      <MatteEnvironment
        cameraState={cameraState}
        reducedMotion={reducedMotion}
      />

      <StarLayer
        count={farCount}
        radius={65}
        depth={65}
        seed={91801}
        size={0.075}
        opacity={0.55}
        parallax={0.045}
        cameraState={cameraState}
      />

      <StarLayer
        count={middleCount}
        radius={38}
        depth={30}
        seed={91802}
        size={0.055}
        opacity={0.46}
        parallax={0.12}
        cameraState={cameraState}
      />

      <StarLayer
        count={nearCount}
        radius={19}
        depth={15}
        seed={91803}
        size={0.038}
        opacity={0.34}
        parallax={0.3}
        cameraState={cameraState}
      />

      <NearDust
        quality={quality}
        cameraState={cameraState}
        reducedMotion={reducedMotion}
      />

      <OpticalFlare
        cameraState={cameraState}
        reducedMotion={reducedMotion}
      />
    </>
  );
}

export function useCinematicPointerControls(
  elementRef,
  cameraState,
  reducedMotion
) {
  useEffect(() => {
    const element =
      elementRef.current;

    if (
      !element ||
      reducedMotion
    ) {
      return undefined;
    }

    const data =
      cameraState.current;

    function down(event) {
      if (
        event.pointerType === "mouse" &&
        event.button !== 0
      ) {
        return;
      }

      data.dragging = true;
      data.pointerId =
        event.pointerId;
      data.lastX =
        event.clientX;
      data.lastY =
        event.clientY;
      data.yawVelocity = 0;
      data.pitchVelocity = 0;

      element.setPointerCapture?.(
        event.pointerId
      );

      element.classList.add(
        "is-camera-dragging"
      );
    }

    function move(event) {
      if (
        !data.dragging ||
        event.pointerId !==
          data.pointerId
      ) {
        return;
      }

      const dx =
        event.clientX -
        data.lastX;

      const dy =
        event.clientY -
        data.lastY;

      data.lastX =
        event.clientX;

      data.lastY =
        event.clientY;

      const sensitivity =
        event.pointerType === "touch"
          ? 0.0044
          : 0.0034;

      const yawDelta =
        -dx * sensitivity;

      const pitchDelta =
        -dy * sensitivity;

      data.targetYaw =
        THREE.MathUtils.clamp(
          data.targetYaw +
            yawDelta,
          -0.72,
          0.72
        );

      data.targetPitch =
        THREE.MathUtils.clamp(
          data.targetPitch +
            pitchDelta,
          -0.38,
          0.38
        );

      data.yawVelocity =
        yawDelta * 60;

      data.pitchVelocity =
        pitchDelta * 60;
    }

    function up(event) {
      if (
        event.pointerId !==
          data.pointerId
      ) {
        return;
      }

      data.dragging = false;
      data.pointerId = null;

      element.releasePointerCapture?.(
        event.pointerId
      );

      element.classList.remove(
        "is-camera-dragging"
      );
    }

    function cancel(event) {
      up(event);
    }

    element.addEventListener(
      "pointerdown",
      down
    );

    element.addEventListener(
      "pointermove",
      move
    );

    element.addEventListener(
      "pointerup",
      up
    );

    element.addEventListener(
      "pointercancel",
      cancel
    );

    return () => {
      element.removeEventListener(
        "pointerdown",
        down
      );

      element.removeEventListener(
        "pointermove",
        move
      );

      element.removeEventListener(
        "pointerup",
        up
      );

      element.removeEventListener(
        "pointercancel",
        cancel
      );
    };
  }, [
    elementRef,
    cameraState,
    reducedMotion
  ]);
}
