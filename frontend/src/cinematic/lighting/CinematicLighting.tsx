import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import { smooth } from "../config/cinematic";
import type { QualityProfile } from "../config/quality";

export function CinematicLighting({
  time,
  quality,
}: {
  time: React.MutableRefObject<number>;
  quality: QualityProfile;
}) {
  const key = useRef<THREE.SpotLight>(null),
    rim = useRef<THREE.SpotLight>(null);
  useFrame(() => {
    const t = time.current,
      forge = smooth(11.8, 14.4, t),
      recognition = smooth(15, 17, t);
    if (key.current) key.current.intensity = 2 + forge * 34 - recognition * 8;
    if (rim.current) rim.current.intensity = 1 + forge * 22;
  });
  return (
    <>
      <ambientLight intensity={0.08} color="#829aae" />
      <spotLight
        ref={key}
        position={[-6, 9, 8]}
        color="#ffd2a1"
        intensity={2}
        angle={0.32}
        penumbra={0.86}
        distance={42}
        castShadow={quality.shadows}
        shadow-mapSize={[quality.shadowSize, quality.shadowSize]}
        shadow-bias={-0.0002}
      />
      <spotLight
        ref={rim}
        position={[7, 4, -5]}
        color="#72ddff"
        intensity={1}
        angle={0.38}
        penumbra={0.9}
        distance={36}
      />
      <pointLight
        position={[0, 0, 2]}
        color="#ccf8ff"
        intensity={2.5}
        distance={8}
      />
    </>
  );
}
