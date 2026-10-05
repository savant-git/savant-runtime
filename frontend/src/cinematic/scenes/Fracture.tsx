import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { smooth } from "../config/cinematic";
import type { QualityProfile } from "../config/quality";
import { seededRandom } from "../particles/seeded";

export function Fracture({
  time,
  quality,
}: {
  time: React.MutableRefObject<number>;
  quality: QualityProfile;
}) {
  const mesh = useRef<THREE.InstancedMesh>(null),
    material = useRef<THREE.MeshPhysicalMaterial>(null),
    random = useMemo(() => seededRandom(404), []);
  const data = useMemo(
    () =>
      Array.from({ length: quality.fragments }, () => ({
        dir: new THREE.Vector3(
          random() - 0.5,
          random() - 0.5,
          random() - 0.5,
        ).normalize(),
        spin: new THREE.Vector3(random() * 3, random() * 3, random() * 3),
        scale: 0.035 + random() * 0.16,
      })),
    [quality.fragments, random],
  );
  useEffect(
    () => () => {
      mesh.current?.dispose();
    },
    [],
  );
  useFrame(() => {
    if (!mesh.current || !material.current) return;
    const t = time.current,
      emerge = smooth(3, 4.4, t),
      reorganize = smooth(5.2, 7.2, t),
      dummy = new THREE.Object3D();
    data.forEach((d, i) => {
      const radius = emerge * (1.2 + (i % 17) * 0.13);
      dummy.position.copy(d.dir).multiplyScalar(radius);
      dummy.position.applyAxisAngle(
        new THREE.Vector3(0, 1, 0),
        (i * 0.618 + t * 0.12) * (1 - reorganize * 0.4),
      );
      dummy.position.lerp(
        new THREE.Vector3(
          Math.sin(i * 0.7) * 2.8,
          ((i % 11) - 5) * 0.22,
          Math.cos(i * 0.43) * 1.8,
        ),
        reorganize,
      );
      dummy.rotation.set(d.spin.x * t, d.spin.y * t, d.spin.z * t);
      dummy.scale.setScalar(d.scale * (1 + reorganize * 1.4));
      dummy.updateMatrix();
      mesh.current!.setMatrixAt(i, dummy.matrix);
    });
    mesh.current.instanceMatrix.needsUpdate = true;
    const phase = Math.floor(Math.max(0, t - 3) * 1.2) % 5;
    material.current.color.set(
      ["#090b0e", "#47606a", "#803d20", "#c7d4d7", "#20252b"][phase],
    );
    material.current.metalness = phase === 3 ? 0.15 : 0.82;
    material.current.roughness = phase === 1 ? 0.66 : 0.18;
  });
  return (
    <instancedMesh
      ref={mesh}
      args={[undefined, undefined, data.length]}
      frustumCulled={false}
    >
      <tetrahedronGeometry args={[1, 0]} />
      <meshPhysicalMaterial
        ref={material}
        color="#080a0d"
        metalness={0.86}
        roughness={0.18}
        clearcoat={0.8}
        transmission={0}
      />
    </instancedMesh>
  );
}
