import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { smooth } from "../config/cinematic";
import type { QualityProfile } from "../config/quality";
import { seededRandom } from "../particles/seeded";

export function SavantAwakening({
  time,
  quality,
}: {
  time: React.MutableRefObject<number>;
  quality: QualityProfile;
}) {
  const nodes = useRef<THREE.InstancedMesh>(null),
    links = useRef<THREE.LineSegments>(null);
  const data = useMemo(() => {
    const random = seededRandom(707),
      points = Array.from(
        { length: quality.latticeNodes },
        (_, i) =>
          new THREE.Vector3(
            (random() - 0.5) * 7,
            (random() - 0.5) * 4,
            (random() - 0.5) * 4 - Math.sin(i) * 0.4,
          ),
      );
    const pairs: number[] = [];
    points.forEach((p, i) => {
      const nearest = points
        .map((q, j) => ({ j, d: p.distanceTo(q) }))
        .filter((x) => x.j !== i)
        .sort((a, b) => a.d - b.d)
        .slice(0, 2);
      nearest.forEach((n) =>
        pairs.push(...p.toArray(), ...points[n.j].toArray()),
      );
    });
    return { points, pairs: new Float32Array(pairs) };
  }, [quality.latticeNodes]);
  const lineGeometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(data.pairs, 3));
    return g;
  }, [data.pairs]);
  useFrame(() => {
    const t = time.current,
      live = smooth(7, 9, t) * (1 - smooth(12, 13.3, t)),
      dummy = new THREE.Object3D();
    data.points.forEach((p, i) => {
      dummy.position.copy(p).multiplyScalar(0.35 + live * 0.65);
      const pulse =
        Math.max(0.04, Math.sin(t * 4 - i * 0.37) * 0.5 + 0.5) * live;
      dummy.scale.setScalar(0.025 + pulse * 0.055);
      dummy.updateMatrix();
      nodes.current?.setMatrixAt(i, dummy.matrix);
    });
    if (nodes.current) nodes.current.instanceMatrix.needsUpdate = true;
    if (links.current)
      (links.current.material as THREE.LineBasicMaterial).opacity = live * 0.24;
  });
  return (
    <group>
      <instancedMesh
        ref={nodes}
        args={[undefined, undefined, data.points.length]}
      >
        <sphereGeometry args={[1, 8, 6]} />
        <meshBasicMaterial color="#8de9ff" toneMapped={false} />
      </instancedMesh>
      <lineSegments ref={links} geometry={lineGeometry}>
        <lineBasicMaterial
          color="#62b9d2"
          transparent
          opacity={0}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </lineSegments>
    </group>
  );
}
