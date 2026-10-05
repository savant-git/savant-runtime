import { useFrame, useThree } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { smooth } from "../config/cinematic";
import { SHOTS } from "../config/shots";

interface CameraProps {
  time: React.MutableRefObject<number>;
  reducedMotion: boolean;
}

export function CinematicCamera({ time, reducedMotion }: CameraProps) {
  const { camera, size } = useThree();
  const perspectiveCamera = camera as THREE.PerspectiveCamera;
  const position = useMemo(() => new THREE.Vector3(), []),
    target = useMemo(() => new THREE.Vector3(), []);
  useFrame(() => {
    const t = time.current;
    if (reducedMotion) {
      camera.position.set(0, 0.2, size.width < size.height ? 12.5 : 10);
      perspectiveCamera.fov = size.width < size.height ? 48 : 42;
      perspectiveCamera.updateProjectionMatrix();
      camera.lookAt(0, 0.2, 0);
      return;
    }
    const current =
      SHOTS.find((s) => t >= s.start && t < s.end) ?? SHOTS[SHOTS.length - 1];
    const index = SHOTS.indexOf(current),
      next = SHOTS[Math.min(index + 1, SHOTS.length - 1)];
    const blend = smooth(
      current.end - Math.min(0.55, (current.end - current.start) * 0.3),
      current.end,
      t,
    );
    position
      .fromArray(current.position)
      .lerp(new THREE.Vector3().fromArray(next.position), blend);
    target
      .fromArray(current.target)
      .lerp(new THREE.Vector3().fromArray(next.target), blend);
    const portrait = size.height > size.width * 1.15;
    camera.position.copy(position);
    if (portrait) {
      camera.position.z += 2.4;
      camera.position.x *= 0.55;
    }
    const impact = current.impact
      ? Math.sin(t * 89) * current.impact * (1 - blend)
      : 0;
    camera.position.x += impact;
    camera.position.y += impact * 0.55;
    perspectiveCamera.fov =
      THREE.MathUtils.lerp(current.fov, next.fov, blend) + (portrait ? 5 : 0);
    perspectiveCamera.updateProjectionMatrix();
    camera.lookAt(target);
  });
  return null;
}
