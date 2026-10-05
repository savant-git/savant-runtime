import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import * as THREE from "three";
import { CinematicCamera } from "./camera/CinematicCamera";
import { QUALITY } from "./config/quality";
import { CinematicLighting } from "./lighting/CinematicLighting";
import { CinematicPost } from "./postprocessing/CinematicPost";
import { FrameQualityGovernor } from "./quality/FrameQualityGovernor";
import { FinalRecognition } from "./scenes/FinalRecognition";
import { Fracture } from "./scenes/Fracture";
import { LogoForge } from "./scenes/LogoForge";
import { SavantAwakening } from "./scenes/SavantAwakening";
import { UnformedSignal } from "./scenes/UnformedSignal";
import type { QualityTier } from "./types";

interface Props {
  time: React.MutableRefObject<number>;
  qualityTier: QualityTier;
  reducedMotion: boolean;
  logoAvailable: boolean;
  onRendererReady: () => void;
  onRendererError: (message: string) => void;
  onQualityDowngrade: (tier: QualityTier) => void;
}

export default function CinematicCanvas({
  time,
  qualityTier,
  reducedMotion,
  logoAvailable,
  onRendererReady,
  onRendererError,
  onQualityDowngrade,
}: Props) {
  const quality = QUALITY[qualityTier];
  return (
    <Canvas
      className="cinematic-canvas"
      dpr={quality.dpr}
      shadows={quality.shadows}
      frameloop="always"
      camera={{ position: [0.2, 0.1, 7.8], fov: 42, near: 0.08, far: 80 }}
      gl={{
        antialias: false,
        alpha: false,
        powerPreference:
          qualityTier === "mobile" ? "default" : "high-performance",
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 0.88,
        outputColorSpace: THREE.SRGBColorSpace,
      }}
      onCreated={({ gl }) => {
        gl.setClearColor("#020304");
        gl.domElement.addEventListener(
          "webglcontextlost",
          (event) => {
            event.preventDefault();
            onRendererError("WebGL context lost");
          },
          { once: true },
        );
        onRendererReady();
      }}
      onError={(error) =>
        onRendererError(
          error instanceof Error
            ? error.message
            : "Renderer initialization failed",
        )
      }
    >
      <color attach="background" args={["#020304"]} />
      <fog attach="fog" args={["#05080b", 9, 34]} />
      <FrameQualityGovernor
        tier={qualityTier}
        onDowngrade={onQualityDowngrade}
      />
      <CinematicCamera time={time} reducedMotion={reducedMotion} />
      <CinematicLighting time={time} quality={quality} />
      <Suspense fallback={null}>
        <UnformedSignal time={time} quality={quality} />
        <Fracture time={time} quality={quality} />
        <SavantAwakening time={time} quality={quality} />
        <LogoForge time={time} logoAvailable={logoAvailable} />
        <FinalRecognition time={time} />
      </Suspense>
      <CinematicPost quality={quality} />
    </Canvas>
  );
}
