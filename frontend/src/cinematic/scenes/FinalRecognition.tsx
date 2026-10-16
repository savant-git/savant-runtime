import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import { smooth } from "../config/cinematic";

export function FinalRecognition({
  time,
}: {
  time: React.MutableRefObject<number>;
}) {
  const ring = useRef<THREE.Mesh>(null);
  useFrame(() => {
    if (!ring.current) return;
    const recognition = smooth(14.2, 16.4, time.current);
    ring.current.rotation.z = time.current * 0.05;
    (ring.current.material as THREE.MeshBasicMaterial).opacity =
      recognition * 0.14;
    ring.current.scale.setScalar(0.8 + recognition * 0.2);
  });
  return (
    <group position={[0, -2.25, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <cylinderGeometry args={[4.6, 5, 0.24, 96]} />
        <meshPhysicalMaterial
          color="#050608"
          metalness={0.82}
          roughness={0.18}
          clearcoat={1}
        />
      </mesh>
      <mesh ref={ring} position={[0, 0.15, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[3.7, 3.74, 128]} />
        <meshBasicMaterial
          color="#91efff"
          transparent
          opacity={0}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}
