import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { QualityTier } from "../types";

const nextTier: Partial<Record<QualityTier, QualityTier>> = {
  ultra: "standard",
  standard: "mobile",
};

export function FrameQualityGovernor({
  tier,
  onDowngrade,
}: {
  tier: QualityTier;
  onDowngrade: (tier: QualityTier) => void;
}) {
  const sample = useRef({ frames: 0, elapsed: 0, settled: false });
  useFrame((_, delta) => {
    const value = sample.current;
    if (value.settled || !nextTier[tier]) return;
    if (delta > 0.25) return;
    value.frames += 1;
    value.elapsed += delta;
    if (value.frames < 120) return;
    value.settled = true;
    if ((value.elapsed / value.frames) * 1000 > 28)
      onDowngrade(nextTier[tier]!);
  });
  return null;
}
