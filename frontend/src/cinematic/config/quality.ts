import type { QualityTier } from "../types";

export interface QualityProfile {
  dpr: [number, number];
  particles: number;
  fragments: number;
  latticeNodes: number;
  shadows: boolean;
  shadowSize: number;
  postprocessing: boolean;
  dof: boolean;
  chromaticAberration: boolean;
}

export const QUALITY: Record<QualityTier, QualityProfile> = {
  ultra: {
    dpr: [1, 2],
    particles: 42000,
    fragments: 620,
    latticeNodes: 160,
    shadows: true,
    shadowSize: 2048,
    postprocessing: true,
    dof: true,
    chromaticAberration: true,
  },
  standard: {
    dpr: [1, 1.5],
    particles: 20000,
    fragments: 340,
    latticeNodes: 100,
    shadows: true,
    shadowSize: 1024,
    postprocessing: true,
    dof: true,
    chromaticAberration: false,
  },
  mobile: {
    dpr: [0.75, 1],
    particles: 6500,
    fragments: 150,
    latticeNodes: 58,
    shadows: false,
    shadowSize: 512,
    postprocessing: true,
    dof: false,
    chromaticAberration: false,
  },
  essential: {
    dpr: [0.75, 1],
    particles: 0,
    fragments: 0,
    latticeNodes: 0,
    shadows: false,
    shadowSize: 0,
    postprocessing: false,
    dof: false,
    chromaticAberration: false,
  },
};
