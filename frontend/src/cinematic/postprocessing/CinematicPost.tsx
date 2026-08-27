import {
  Bloom,
  ChromaticAberration,
  DepthOfField,
  EffectComposer,
  Noise,
  SMAA,
  Vignette,
} from "@react-three/postprocessing";
import { BlendFunction } from "postprocessing";
import * as THREE from "three";
import { POST } from "../config/postprocessing";
import type { QualityProfile } from "../config/quality";

export function CinematicPost({ quality }: { quality: QualityProfile }) {
  if (!quality.postprocessing) return null;
  const effects = [
    <Bloom key="bloom" {...POST.bloom} mipmapBlur />,
    ...(quality.dof ? [<DepthOfField key="dof" {...POST.depthOfField} />] : []),
    ...(quality.chromaticAberration
      ? [
          <ChromaticAberration
            key="chromatic"
            offset={new THREE.Vector2(...POST.chromaticOffset)}
            radialModulation
            modulationOffset={0.42}
          />,
        ]
      : []),
    <Noise
      key="noise"
      opacity={POST.noiseOpacity}
      blendFunction={BlendFunction.SOFT_LIGHT}
    />,
    <Vignette key="vignette" {...POST.vignette} eskil={false} />,
    <SMAA key="smaa" />,
  ];
  return (
    <EffectComposer multisampling={quality.dof ? 4 : 0}>
      {effects}
    </EffectComposer>
  );
}
