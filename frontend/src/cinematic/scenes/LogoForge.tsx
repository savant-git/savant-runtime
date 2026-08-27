import { useFrame, useLoader } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { smooth } from "../config/cinematic";

function ApprovedLogo({ time }: { time: React.MutableRefObject<number> }) {
  const { scene } = useLoader(GLTFLoader, "/cinematic/savant-logo.glb"),
    group = useRef<THREE.Group>(null);
  const model = useMemo(() => {
    const clone = scene.clone(true);
    const box = new THREE.Box3().setFromObject(clone),
      size = box.getSize(new THREE.Vector3()),
      center = box.getCenter(new THREE.Vector3());
    clone.position.sub(center);
    clone.scale.setScalar(5 / Math.max(size.x, size.y, size.z));
    clone.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) {
        const m = o as THREE.Mesh;
        m.castShadow = true;
        m.material = new THREE.MeshPhysicalMaterial({
          color: "#111318",
          metalness: 0.72,
          roughness: 0.2,
          clearcoat: 1,
          clearcoatRoughness: 0.06,
        });
      }
    });
    return clone;
  }, [scene]);
  useFrame(() => {
    if (!group.current) return;
    const forged = smooth(12.1, 15.2, time.current);
    group.current.scale.setScalar(0.01 + forged * 0.99);
    group.current.rotation.y = (1 - forged) * 1.2;
    group.current.position.y = (1 - forged) * -1.8;
  });
  return (
    <group ref={group}>
      <primitive object={model} />
    </group>
  );
}

export function LogoForge({
  time,
  logoAvailable,
}: {
  time: React.MutableRefObject<number>;
  logoAvailable: boolean;
}) {
  const shock = useRef<THREE.Mesh>(null);
  useFrame(() => {
    if (!shock.current) return;
    const p =
      smooth(12, 12.45, time.current) * (1 - smooth(12.8, 13.6, time.current));
    shock.current.scale.setScalar(0.1 + p * 8);
    (shock.current.material as THREE.MeshBasicMaterial).opacity = p * 0.32;
  });
  return (
    <group>
      <mesh ref={shock} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.96, 1, 128]} />
        <meshBasicMaterial
          color="#d9fbff"
          transparent
          opacity={0}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
      {logoAvailable && <ApprovedLogo time={time} />}
      <pointLight position={[-4, 4, 5]} color="#ffd19a" intensity={18} />
      <pointLight position={[4, 1, -3]} color="#66dfff" intensity={12} />
    </group>
  );
}
