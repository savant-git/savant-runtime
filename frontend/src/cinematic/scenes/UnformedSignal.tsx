import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { smooth } from "../config/cinematic";
import type { QualityProfile } from "../config/quality";
import { seededRandom } from "../particles/seeded";

export function UnformedSignal({
  time,
  quality,
}: {
  time: React.MutableRefObject<number>;
  quality: QualityProfile;
}) {
  const signal = useRef<THREE.Mesh>(null),
    dust = useRef<THREE.Points>(null);
  const geometry = useMemo(() => {
    const count = Math.max(800, Math.floor(quality.particles * 0.18)),
      random = seededRandom(101),
      p = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 2 + random() * 16,
        a = random() * Math.PI * 2;
      p.set(
        [Math.cos(a) * r, (random() - 0.5) * 8, Math.sin(a) * r - 4],
        i * 3,
      );
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(p, 3));
    return g;
  }, [quality.particles]);
  useFrame((_, delta) => {
    const t = time.current,
      visible = 1 - smooth(3, 4.2, t);
    if (signal.current) {
      signal.current.scale.setScalar(
        0.08 + smooth(1.2, 3, t) * (0.9 + Math.sin(t * 7) * 0.08),
      );
      (signal.current.material as THREE.MeshBasicMaterial).opacity = visible;
    }
    if (dust.current) {
      dust.current.rotation.y += delta * 0.012;
      (dust.current.material as THREE.PointsMaterial).opacity = 0.14 * visible;
    }
  });
  return (
    <group>
      <points ref={dust} geometry={geometry}>
        <pointsMaterial
          color="#78909d"
          size={0.018}
          transparent
          opacity={0.12}
          depthWrite={false}
        />
      </points>
      <mesh ref={signal}>
        <icosahedronGeometry args={[0.32, 4]} />
        <meshBasicMaterial
          color="#fff4cf"
          transparent
          opacity={0}
          toneMapped={false}
        />
      </mesh>
      <pointLight color="#8edcff" intensity={7} distance={8} />
    </group>
  );
}
