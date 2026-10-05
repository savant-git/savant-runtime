import {
  useEffect,
  useRef
} from "react";

import {
  useFrame
} from "@react-three/fiber";

import * as THREE from "three";

const modeProfiles = {
  earth: {
    earth: 1,
    moon: 0.72,
    mars: 0.38,
    spacecraft: 0.72,
    orbital: 0.48,
    foreground: 0.72
  },

  transit: {
    earth: 0.82,
    moon: 0.82,
    mars: 0.52,
    spacecraft: 1,
    orbital: 1,
    foreground: 1
  },

  moon: {
    earth: 0.5,
    moon: 1,
    mars: 0.32,
    spacecraft: 0.78,
    orbital: 0.74,
    foreground: 0.7
  },

  gateway: {
    earth: 0.46,
    moon: 0.9,
    mars: 0.28,
    spacecraft: 1,
    orbital: 0.86,
    foreground: 0.68
  }
};

function resolveProfile(
  mode
) {
  return (
    modeProfiles[mode] ??
    modeProfiles.transit
  );
}

function updateGroupOpacity(
  group,
  opacity
) {
  if (!group) {
    return;
  }

  group.traverse(
    object => {
      if (
        !object.material
      ) {
        return;
      }

      const materials =
        Array.isArray(
          object.material
        )
          ? object.material
          : [
              object.material
            ];

      materials.forEach(
        material => {
          if (
            !material.userData
              .cinematicBaseOpacity
          ) {
            material.userData
              .cinematicBaseOpacity =
              Number.isFinite(
                material.opacity
              )
                ? material.opacity
                : 1;
          }

          const base =
            material.userData
              .cinematicBaseOpacity;

          material.transparent =
            opacity < 0.999 ||
            material.transparent;

          material.opacity =
            base * opacity;
        }
      );
    }
  );
}

function DirectedGroup({
  channel,
  mode,
  children
}) {
  const group =
    useRef();

  const opacity =
    useRef(
      resolveProfile(
        mode
      )[channel] ?? 1
    );

  useEffect(() => {
    updateGroupOpacity(
      group.current,
      opacity.current
    );
  }, []);

  useFrame(
    (
      state,
      delta
    ) => {
      if (!group.current) {
        return;
      }

      const target =
        resolveProfile(
          mode
        )[channel] ?? 1;

      opacity.current =
        THREE.MathUtils.damp(
          opacity.current,
          target,
          3,
          delta
        );

      updateGroupOpacity(
        group.current,
        opacity.current
      );
    }
  );

  return (
    <group ref={group}>
      {children}
    </group>
  );
}

export function EarthDirector({
  mode,
  children
}) {
  return (
    <DirectedGroup
      channel="earth"
      mode={mode}
    >
      {children}
    </DirectedGroup>
  );
}

export function MoonDirector({
  mode,
  children
}) {
  return (
    <DirectedGroup
      channel="moon"
      mode={mode}
    >
      {children}
    </DirectedGroup>
  );
}

export function MarsDirector({
  mode,
  children
}) {
  return (
    <DirectedGroup
      channel="mars"
      mode={mode}
    >
      {children}
    </DirectedGroup>
  );
}

export function SpacecraftDirector({
  mode,
  children
}) {
  return (
    <DirectedGroup
      channel="spacecraft"
      mode={mode}
    >
      {children}
    </DirectedGroup>
  );
}

export function OrbitalDirector({
  mode,
  children
}) {
  return (
    <DirectedGroup
      channel="orbital"
      mode={mode}
    >
      {children}
    </DirectedGroup>
  );
}

export function ForegroundDirector({
  mode,
  children
}) {
  return (
    <DirectedGroup
      channel="foreground"
      mode={mode}
    >
      {children}
    </DirectedGroup>
  );
}
