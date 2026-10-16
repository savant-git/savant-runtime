import React, { useEffect, useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { AdditiveBlending, BufferGeometry, CatmullRomCurve3, Color, Float32BufferAttribute, Mesh, ShaderMaterial, Vector3 } from "three"
import { glitchState } from "./savant-motion"
import { savantContour, savantContourFrontZ } from "./savant-contour-data"

// All three systems use one contour clock, so color, creation and decay stay registered.
const rate = .095
const life = 12.8
const spacing = .2
const gold = "#e5ad39"
const pink = "#ec368e"
const tau = Math.PI * 2
const fract = (v: number) => v - Math.floor(v)
const pointCount = Math.max(1, Math.round(1 / (rate * spacing)))
const contour = new CatmullRomCurve3(savantContour.map(([x, y]) => new Vector3(x, y, 0)), true, "centripetal", .5)
const halfDepth = Math.abs(savantContourFrontZ) + .065
const contourPoint = (phase: number, side: number) => {
  const p = contour.getPointAt(fract(phase))
  const tangent = contour.getTangentAt(fract(phase)).normalize()
  const normal = new Vector3(-tangent.y, tangent.x, 0)
  // Offset away from the model's perimeter instead of drawing directly on its face.
  p.addScaledVector(normal, .034)
  p.z = side * halfDepth
  return p
}

type LineData = { geometry: BufferGeometry; count: number }
function makeLines(lines: Array<{ a: Vector3; b: Vector3; phase: number; from: number; to: number; seed: number; family: number }>): LineData {
  const pos: number[] = [], phase: number[] = [], progress: number[] = [], seed: number[] = [], family: number[] = []
  for (const l of lines) {
    pos.push(...l.a.toArray(), ...l.b.toArray())
    phase.push(l.phase, l.phase)
    progress.push(l.from, l.to)
    seed.push(l.seed, l.seed)
    family.push(l.family, l.family)
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute("position", new Float32BufferAttribute(pos, 3))
  geometry.setAttribute("aPhase", new Float32BufferAttribute(phase, 1))
  geometry.setAttribute("aProgress", new Float32BufferAttribute(progress, 1))
  geometry.setAttribute("aSeed", new Float32BufferAttribute(seed, 1))
  geometry.setAttribute("aFamily", new Float32BufferAttribute(family, 1))
  return { geometry, count: lines.length }
}
function buildStructure() {
  const lines: Array<{ a: Vector3; b: Vector3; phase: number; from: number; to: number; seed: number; family: number }> = []
  const add = (a: Vector3, b: Vector3, phase: number, from: number, to: number, seed: number, family: number) => lines.push({ a, b, phase, from, to, seed, family })
  // Contour samples and connectors share one source clock and deterministic geometry.
  const edgeSteps = 1600
  for (let side of [-1, 1]) for (let i = 0; i < edgeSteps; i++) {
    const p = i / edgeSteps
    add(contourPoint(p, side), contourPoint((i + 1) / edgeSteps, side), p, 0, 0, i + side * 7, 0)
  }
  // Interlocking three-prong rows are swept over a gently curved extrusion depth.
  for (let i = 0; i < pointCount; i++) {
    const phase = i / pointCount
    const base = contourPoint(phase, 1)
    const tangent = contour.getTangentAt(phase).normalize()
    const normal = new Vector3(-tangent.y, tangent.x, 0)
    const across = (t: number, offset: number) => {
      const z = halfDepth * (1 - 2 * t)
      const curvature = .025 * Math.sin(Math.PI * t)
      return new Vector3(base.x, base.y, z).addScaledVector(normal, curvature + offset)
    }
    const steps = 24
    for (let j = 0; j < steps; j++) {
      const t = j / steps, next = (j + 1) / steps
      const zig = (v: number) => .035 * Math.sin(v * Math.PI * 6)
      add(across(t, zig(t)), across(next, zig(next)), phase, t * .7, next * .7, i, 1)
    }
    for (let j = 0; j < 6; j++) {
      const t = (j + .5) / 6
      const c = across(t, .035 * Math.sin(t * Math.PI * 6))
      add(c, across(Math.min(1, t + .065), .075), phase, .70 + j * .025, .7125 + j * .025, i, 1)
      add(c, across(Math.min(1, t + .065), -.075), phase, .7125 + j * .025, .725 + j * .025, i, 1)
    }
    // Rounded fourfold ornaments at the known row/contour junctions.
    for (const side of [-1, 1]) {
      const anchor = contourPoint(phase, side)
      const radius = .024
      const segments = 28
      for (let k = 0; k < segments; k++) {
        const knot = (v: number) => {
          const angle = tau * v / segments
          const r = radius * (1 + .26 * Math.cos(4 * angle))
          return anchor.clone().addScaledVector(normal, Math.cos(angle) * r).addScaledVector(tangent, Math.sin(angle) * r)
        }
        add(knot(k), knot(k + 1), phase, .85 + .15 * k / segments, .85 + .15 * (k + 1) / segments, i, 2)
      }
    }
  }
  // Paired helices wrap the actual contour instead of wandering through empty space.
  const coils = 4, steps = 1600
  for (const side of [-1, 1]) for (let i = 0; i < steps; i++) {
    const helix = (t: number) => {
      const p = contourPoint(t, side)
      const tangent = contour.getTangentAt(fract(t)).normalize()
      const normal = new Vector3(-tangent.y, tangent.x, 0)
      const angle = tau * coils * t
      return p.addScaledVector(normal, .12 * Math.cos(angle)).add(new Vector3(0, 0, .12 * Math.sin(angle)))
    }
    add(helix(i / steps), helix((i + 1) / steps), i / steps, 0, 0, i + side * 13, 3)
  }
  return makeLines(lines)
}

function luminousMaterial(color: string, glow: boolean) {
  return new ShaderMaterial({
    transparent: true, depthWrite: false, depthTest: true,
    blending: glow ? AdditiveBlending : undefined,
    toneMapped: false,
    uniforms: { uTime: { value: 0 }, uActive: { value: 0 }, uGlitch: { value: 0 }, uGold: { value: new Color(color) }, uPink: { value: new Color(pink) }, uGlow: { value: glow ? 1 : 0 } },
    vertexShader: `attribute float aPhase,aProgress,aSeed,aFamily;
      varying float vPhase,vProgress,vFamily;
      uniform float uTime,uGlitch;
      void main(){vPhase=aPhase;vProgress=aProgress;vFamily=aFamily;vec3 p=position;
        float ribbon=sin(aPhase*19.0-uTime*13.0+position.z*3.0);
        float swell=sin(aPhase*9.0+uTime*7.0+position.x*4.0);
        float loose=uGlitch*(0.045+0.035*(0.5+0.5*swell));
        p.xy+=vec2(ribbon,swell)*loose;
        p.z+=uGlitch*0.035*sin(aPhase*12.0+uTime*8.0);
        gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);
      }`,
    fragmentShader: `varying float vPhase,vProgress,vFamily;
      uniform float uTime,uActive,uGlow;uniform vec3 uGold,uPink;
      void main(){
        float head=fract(uTime*${rate.toFixed(6)});
        float age=fract(head-vPhase+1.0)/${rate.toFixed(6)};
        float fade=1.0-smoothstep(${(life - 2).toFixed(2)},${life.toFixed(2)},age);
        float draw=vFamily<0.5||vFamily>2.5?1.0:smoothstep(vProgress-0.025,vProgress+0.025,clamp(age/${spacing.toFixed(3)},0.0,1.0));
        float rose=smoothstep(${(life * .43).toFixed(3)},${(life * .62).toFixed(3)},age);
        float pulse=0.82+0.18*pow(0.5+0.5*sin(uTime*1.8),2.0);
        float alpha=uActive*fade*draw*pulse*(uGlow>0.5?0.12:0.88);
        if(alpha<0.005)discard;
        vec3 c=mix(uGold,uPink,rose);
        gl_FragColor=vec4(c*(uGlow>0.5?1.25:1.0),alpha);
      }`,
  })
}

export function SavantContourLight({ time, active, color = gold }: {
  time: React.MutableRefObject<number>; active: boolean; color?: string
}) {
  const structure = useMemo(buildStructure, [])
  const core = useMemo(() => luminousMaterial(color, false), [color])
  const glow = useMemo(() => luminousMaterial(color, true), [color])
  const heads = useRef<Array<Mesh | null>>([])
  const lastGlitch = useRef(false)
  const sparks = useRef<Array<Mesh | null>>([])
  const sparkStart = useRef(-100)
  useEffect(() => () => { structure.geometry.dispose(); core.dispose(); glow.dispose() }, [structure, core, glow])
  useFrame(() => {
    const t = time.current, glitch = glitchState(t).amount
    for (const m of [core, glow]) {
      m.uniforms.uTime.value = t
      m.uniforms.uGlitch.value = glitch
      m.uniforms.uActive.value = active ? 1 : 0
    }
    if (lastGlitch.current && glitch <= .001) sparkStart.current = t
    lastGlitch.current = glitch > .001
    const phase = fract(t * rate)
    for (let i = 0; i < 4; i++) {
      const mesh = heads.current[i]
      if (!mesh) continue
      const side = i % 2 ? -1 : 1
      const p = contourPoint(phase, side)
      if (i > 1) {
        const angle = tau * 4 * phase
        const tangent = contour.getTangentAt(phase).normalize()
        p.addScaledVector(new Vector3(-tangent.y, tangent.x, 0), .12 * Math.cos(angle))
        p.z += .12 * Math.sin(angle)
      }
      mesh.position.copy(p)
      mesh.rotation.set(t * 3.3 + i, t * 5.2, t * 4.1 - i)
      mesh.visible = active
    }
    const age = t - sparkStart.current
    for (let i = 0; i < sparks.current.length; i++) {
      const s = sparks.current[i]
      if (!s) continue
      s.visible = active && age >= 0 && age < 2
      if (!s.visible) continue
      const owner = heads.current[i % 4]
      if (!owner) continue
      const angle = tau * (i / sparks.current.length)
      const spread = age < 1 ? age : 2 - age
      const r = .02 + .24 * Math.max(0, spread)
      s.position.copy(owner.position).add(new Vector3(Math.cos(angle) * r, Math.sin(angle * 2.7) * r, Math.sin(angle) * r))
      s.scale.setScalar(.3 * Math.max(0, age < 1 ? 1 : 2 - age))
    }
  })
  return <group>
    <lineSegments geometry={structure.geometry} material={glow} frustumCulled={false} />
    <lineSegments geometry={structure.geometry} material={core} frustumCulled={false} />
    {Array.from({ length: 4 }, (_, i) => <mesh key={i} ref={el => { heads.current[i] = el }}>
      <icosahedronGeometry args={[.083, 0]} />
      <meshPhysicalMaterial color="#070b11" metalness={1} roughness={.065} clearcoat={1} envMapIntensity={2.5} />
      <pointLight color={color} intensity={2.2} distance={.85} decay={2} />
    </mesh>)}
    {Array.from({ length: 32 }, (_, i) => <mesh key={`spark-${i}`} ref={el => { sparks.current[i] = el }} visible={false}>
      <tetrahedronGeometry args={[.022, 0]} />
      <meshBasicMaterial color={i % 4 === 0 ? pink : color} toneMapped={false} />
    </mesh>)}
  </group>
}
