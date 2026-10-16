import React, { Suspense, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { createPortal as createDomPortal } from "react-dom"
import { Canvas, createPortal, useFrame, useThree } from "@react-three/fiber"
import { useGLTF } from "@react-three/drei"
import { ACESFilmicToneMapping, AdditiveBlending, BackSide, Box3, Color, CubeCamera, DoubleSide, BufferAttribute, BufferGeometry, DynamicDrawUsage, EdgesGeometry, Group, HalfFloatType, InstancedMesh, MathUtils, Matrix4, Mesh, MeshDepthMaterial, MeshPhysicalMaterial, Object3D, PerspectiveCamera, PointLight, RGBADepthPacking, Scene, ShaderMaterial, ShadowMaterial, Vector3, WebGLCubeRenderTarget } from "three"
import { materialPresets, installSurface, applyAppearance, legacyPresetIds } from "./savant-surfaces"
import type { MaterialPreset, EffectUniforms } from "./savant-surfaces"
import { CinematicParticles } from "./savant-particles"
import { glitchState, damp } from "./savant-motion"
import { AtmosphereGlow, ReflectionLighting } from "./savant-atmosphere"
import "./savant-mark.css"
import "../workspace/palaver-industrial.css"

const assetUrl = "/cinematic/savant_logo.glb"
const revolutionSeconds = 8
const fullTurn = Math.PI * 2

export type SavantMarkMode = "header" | "preloader"
export type SavantMarkState =
  | "idle" | "thinking" | "streaming" | "tool"
  | "complete" | "degraded" | "failure"

type SavantMarkProps = {
  mode?: SavantMarkMode
  state?: SavantMarkState
  className?: string
  label?: string
  progress?: number
  active?: boolean
}

type MarkSceneProps = {
  mode: SavantMarkMode
  state: SavantMarkState
  active: boolean
  preset: MaterialPreset
  interaction: React.MutableRefObject<Interaction>
  revision: number
  reducedMotion: boolean
}


type Interaction = { yaw: number; pitch: number; dragging: boolean }
function useMaterialPreset() {
  const [id, setId] = useState(() => {
    try { return localStorage.getItem("savant-logo-material-v1") || "white-chrome" }
    catch { return "white-chrome" }
  })
  useEffect(() => {
    const sync = () => {
      try { setId(localStorage.getItem("savant-logo-material-v1") || "white-chrome") }
      catch {}
    }
    const custom = (event: Event) => setId((event as CustomEvent<string>).detail)
    window.addEventListener("storage", sync)
    window.addEventListener("savant-logo-material", custom)
    return () => {
      window.removeEventListener("storage", sync)
      window.removeEventListener("savant-logo-material", custom)
    }
  }, [])
  const choose = (next: string) => {
    if (!materialPresets.some(preset => preset.id === next)) return
    setId(next)
    try { localStorage.setItem("savant-logo-material-v1", next) } catch {}
    window.dispatchEvent(new CustomEvent("savant-logo-material", { detail: next }))
  }
  return { preset: materialPresets.find(preset => preset.id === (legacyPresetIds[id] || id)) || materialPresets[0], choose }
}

const effectsPalette = { pink: "#ff2f9d", gold: "#d6b45f" }

function glitchAmount(time:number){return glitchState(time).amount}

function shadowReceiverMaterial() {
  const material = new ShadowMaterial({
    opacity: 0.32, transparent: true, depthWrite: false,
  })
  material.onBeforeCompile = shader => {
    if (!shader.vertexShader.includes("#include <common>") ||
        !shader.vertexShader.includes("#include <begin_vertex>") ||
        !shader.vertexShader.includes("#include <shadowmap_vertex>") ||
        !shader.fragmentShader.includes("#include <common>") ||
        !shader.fragmentShader.includes("#include <fog_fragment>")) return
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vSavantShadow;\n")
      .replace("#include <begin_vertex>",
        "#include <begin_vertex>\nvSavantShadow = position.xy / 5.0 + 0.5;\n")
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vSavantShadow;\n")
      .replace("#include <fog_fragment>",
        `gl_FragColor.a *= smoothstep(0.0, 0.42, vSavantShadow.y)
          * smoothstep(0.0, 0.14, vSavantShadow.x)
          * (1.0 - smoothstep(0.86, 1.0, vSavantShadow.x));
        #include <fog_fragment>`)
  }
  material.customProgramCacheKey = () => "savant-logo-diagonal-shadow-v1"
  return material
}

function useAnimationVisibility(root: React.RefObject<HTMLDivElement | null>) {
  const [visible, setVisible] = useState(true)
  useEffect(() => {
    let intersects = true
    const update = () => setVisible(intersects && !document.hidden)
    const observer = typeof IntersectionObserver === "undefined" ? null :
      new IntersectionObserver(entries => {
        intersects = entries.some(entry => entry.isIntersecting)
        update()
      })
    if (root.current) observer?.observe(root.current)
    document.addEventListener("visibilitychange", update)
    update()
    return () => {
      observer?.disconnect()
      document.removeEventListener("visibilitychange", update)
    }
  }, [root])
  return visible
}

function useReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(
    () => typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  )
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => setReducedMotion(query.matches)
    update()
    query.addEventListener("change", update)
    return () => query.removeEventListener("change", update)
  }, [])
  return reducedMotion
}

/* Geometry and cached GLB materials remain owned by the loader.
 * Each renderer owns only its cloned hierarchy and chrome materials.
 */
function prepareModel(source: Object3D, uniforms: EffectUniforms) {
  const model = new Group()
  const clone = source.clone(true)
  const materials: MeshPhysicalMaterial[] = []
  const depthMaterials: MeshDepthMaterial[] = []
  clone.traverse(object => {
    if (!(object instanceof Mesh)) return
    const localBounds = new Box3().setFromBufferAttribute(object.geometry.attributes.position)
    const extent = localBounds.getSize(new Vector3())
    const unit = Math.max(extent.x, extent.y, extent.z, 0.0001)
    const depthMaterial = new MeshDepthMaterial({ depthPacking: RGBADepthPacking })
    installSurface(depthMaterial, uniforms, unit)
    depthMaterials.push(depthMaterial)
    const originals = Array.isArray(object.material)
      ? object.material : [object.material]
    const chrome = originals.map(() => {
      const material = new MeshPhysicalMaterial({
        name: "savant-white-chrome",
        color: "#f4f6f8",
        metalness: 1,
        roughness: 0.07,
        clearcoat: 1,
        clearcoatRoughness: 0.025,
        envMapIntensity: 1.55,
        side: DoubleSide,
        transparent: false,
        opacity: 1,
        depthWrite: true,
        iridescence: .001,
        anisotropy: .001,
      })
      installSurface(material, uniforms, unit)
      materials.push(material)
      return material
    })
    object.material = Array.isArray(object.material) ? chrome : chrome[0]
    object.customDepthMaterial = depthMaterial
    object.castShadow = true
    object.receiveShadow = true
  })
  model.add(clone)
  model.updateMatrixWorld(true)
  const bounds = new Box3().setFromObject(model)
  if (!bounds.isEmpty()) {
    const size = bounds.getSize(new Vector3())
    const center = bounds.getCenter(new Vector3())
    const scale = 2 / Math.max(size.x, size.y, size.z, 0.0001)
    model.scale.setScalar(scale)
    model.position.copy(center).multiplyScalar(-scale)
    model.updateMatrixWorld(true)
  }
  return { model, materials, depthMaterials, bounds: new Box3().setFromObject(model) }
}

/* Capture only the reflection stage and matching particle projections.
 * The logo is excluded, avoiding recursive self-reflections. */
function ReflectionCapture({ mode, active, children, version }: {
  mode: SavantMarkMode
  active: boolean
  children: React.ReactNode
  version: string
}) {
  const { gl, scene, invalidate } = useThree()
  const stage = useMemo(() => new Scene(), [])
  const capture = useMemo(() => {
    const target = new WebGLCubeRenderTarget(mode === "header" ? 256 : 512,
      { type: HalfFloatType, generateMipmaps: false })
    return { target, camera: new CubeCamera(0.05, 40, target) }
  }, [mode])
  const elapsed = useRef(1)
  const frameCost = useRef(1 / 60)
  const ready = useRef(false)
  useEffect(() => {
    const previous = scene.environment
    scene.environment = capture.target.texture
    ready.current = false
    elapsed.current = 1
    invalidate()
    return () => {
      if (scene.environment === capture.target.texture) scene.environment = previous
      capture.target.dispose()
    }
  }, [capture, scene, invalidate])
  useEffect(() => { ready.current = false; elapsed.current = 1; invalidate() }, [version, invalidate])
  useFrame((_, delta) => {
    elapsed.current += Math.min(delta, 0.1)
    frameCost.current = frameCost.current * .95 + Math.min(delta, .1) * .05
    const interval = frameCost.current > .024 ? .4 : .16
    if (ready.current && (!active || elapsed.current < interval)) return
    const autoClear = gl.autoClear
    try {
      gl.autoClear = true
      capture.camera.update(gl, stage)
      capture.target.texture.needsPMREMUpdate = true
      ready.current = true
      elapsed.current = 0
    } finally {
      gl.autoClear = autoClear
    }
  }, -1)
  return createPortal(children, stage)
}

const rippleVertex = `
  uniform float uRippleTime;
  varying vec2 vRippleUv;
  void main() {
    vRippleUv = uv;
    vec3 p = position;
    p.x += sin(p.y * 3.2 + uRippleTime * 1.2) * 0.17;
    p.z += sin(p.y * 2.0 - uRippleTime * 0.9) * 0.23;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
  }
`
const rippleFragment = `
  uniform float uRippleTime;
  uniform vec3 uRippleColor;
  varying vec2 vRippleUv;
  void main() {
    float filament = pow(0.5 + 0.5 * sin(vRippleUv.y * 65.0 -
      uRippleTime * 3.4 + vRippleUv.x * 16.0), 6.0);
    float edge = smoothstep(0.0, 0.12, vRippleUv.x) *
      (1.0 - smoothstep(0.88, 1.0, vRippleUv.x));
    gl_FragColor = vec4(uRippleColor * (0.6 + filament * 1.1),
      edge * 0.95);
    #include <colorspace_fragment>
  }
`

function RippleFilaments({ time, preset }: { time: React.MutableRefObject<number>; preset: MaterialPreset }) {
  const materials = useRef<Array<ShaderMaterial | null>>([])
  const colors = useMemo(() =>
    [preset.accent, preset.accent2, preset.color, "#f1e5c7", "#080a0c"].map(color => new Color(color)), [preset])
  const uniforms = useMemo(() => colors.map(color => ({
    uRippleTime: { value: 0 }, uRippleColor: { value: color },
  })), [colors])
  useFrame(() => {
    for (const material of materials.current) {
      if (material) material.uniforms.uRippleTime.value = time.current
    }
  }, -2)
  return (
    <group rotation={[0.05, 0.25, -0.48]} position={[0, 0, -4]}>
      {colors.map((_, index) => (
        <mesh key={index} position={[(index - 2) * 1.3, 0, index * -0.08]}
          scale={[0.38 + index * 0.035, 1, 1]}>
          <planeGeometry args={[1, 9, 4, 64]} />
          <shaderMaterial ref={material => { materials.current[index] = material }}
            uniforms={uniforms[index]} vertexShader={rippleVertex}
            fragmentShader={rippleFragment} transparent side={DoubleSide}
            depthWrite={false} toneMapped={false} />
        </mesh>
      ))}
    </group>
  )
}

/* Surface-sampled pixel fragments exist only during the short glitch.
 * A single instanced draw avoids adding persistent decorative particles. */
function PixelFragments({ model, mode, uniforms, preset }: {
  model: Group
  mode: SavantMarkMode
  uniforms: EffectUniforms
  preset: MaterialPreset
}) {
  const mesh = useRef<InstancedMesh>(null)
  const matrix = useMemo(() => new Matrix4(), [])
  const samples = useMemo(() => {
    model.updateWorldMatrix(true, true)
    const parentInverse = model.parent ? new Matrix4().copy(model.parent.matrixWorld).invert() : new Matrix4()
    const sources: Mesh[] = []
    model.traverse(object => {
      if (object instanceof Mesh && object.geometry.attributes.position) sources.push(object)
    })
    const points: Vector3[] = []
    const count = mode === "header" ? 144 : 240
    for (let index = 0; index < count && sources.length; index++) {
      const source = sources[index % sources.length]
      const attribute = source.geometry.attributes.position
      const vertex = Math.floor(((index * 0.61803398875) % 1) * attribute.count)
      points.push(new Vector3().fromBufferAttribute(attribute, vertex)
        .applyMatrix4(source.matrixWorld).applyMatrix4(parentInverse))
    }
    return points
  }, [model, mode])
  useLayoutEffect(() => {
    if (!mesh.current) return
    mesh.current.instanceMatrix.setUsage(DynamicDrawUsage)
    const color = new Color()
    samples.forEach((_, index) => {
      color.set(index % 7 === 0 ? preset.accent :
        index % 5 === 0 ? preset.accent2 : preset.particle)
      mesh.current?.setColorAt(index, color)
    })
    if (mesh.current.instanceColor) mesh.current.instanceColor.needsUpdate = true
  }, [samples, preset])
  useFrame(() => {
    if (!mesh.current) return
    const amount = uniforms.uSavantGlitch.value
    mesh.current.visible = amount > 0.05
    if (!mesh.current.visible) return
    const tick = Math.floor(uniforms.uSavantTime.value * 48)
    for (let index = 0; index < samples.length; index++) {
      const point = samples[index]
      const noise = Math.sin(index * 17.31 + tick * 2.7)
      const size = (0.013 + (index % 4) * 0.003) * amount * (1 + .8 * Math.abs(noise))
      matrix.makeScale(size * (1 + (index % 3)), size, size)
      matrix.setPosition(
        point.x + noise * (0.24 + .18 * Math.sin(tick * .43 + index)) * amount,
        point.y + Math.sin(index * 4.3) * 0.055 * amount,
        point.z + Math.cos(index * 7.1 + tick) * 0.25 * amount)
      mesh.current.setMatrixAt(index, matrix)
    }
    mesh.current.instanceMatrix.needsUpdate = true
  }, -2)
  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, samples.length]}
      visible={false} frustumCulled={false}>
      <boxGeometry args={[1, 1, 1]} />
      <meshPhysicalMaterial color="#ffffff" metalness={1} roughness={0.12}
        clearcoat={1} clearcoatRoughness={0.04} envMapIntensity={1.7} />
    </instancedMesh>
  )
}


/* Feature edges come from the actual GLB, then graph-connected chains are
 * assigned cumulative distance so a gleam travels along the S contour. */
function contourGeometry(model: Group) {
  model.updateWorldMatrix(true, true)
  const parentInverse = model.parent ?
    new Matrix4().copy(model.parent.matrixWorld).invert() : new Matrix4()
  const edges: Array<[Vector3, Vector3]> = []
  model.traverse(object => {
    if (!(object instanceof Mesh)) return
    const geometry = new EdgesGeometry(object.geometry, 32)
    const positions = geometry.attributes.position
    const transform = new Matrix4().multiplyMatrices(parentInverse, object.matrixWorld)
    for (let index = 0; index < positions.count; index += 2) {
      edges.push([
        new Vector3().fromBufferAttribute(positions, index).applyMatrix4(transform),
        new Vector3().fromBufferAttribute(positions, index + 1).applyMatrix4(transform),
      ])
    }
    geometry.dispose()
  })
  const key = (point: Vector3) => [point.x, point.y, point.z]
    .map(value => Math.round(value * 10000)).join(":")
  const adjacency = new Map<string, number[]>()
  edges.forEach((edge, index) => edge.forEach(point => {
    const id = key(point)
    const entries = adjacency.get(id) || []
    entries.push(index); adjacency.set(id, entries)
  }))
  const visited = new Set<number>()
  const ordered: Array<[Vector3, Vector3]> = []
  for (let seed = 0; seed < edges.length; seed++) {
    if (visited.has(seed)) continue
    let index: number | undefined = seed
    let start = edges[seed][0]
    while (index !== undefined && !visited.has(index)) {
      visited.add(index)
      const edge: [Vector3, Vector3] = key(edges[index][0]) === key(start) ?
        edges[index] : [edges[index][1], edges[index][0]]
      ordered.push(edge)
      start = edge[1]
      index = adjacency.get(key(start))?.find(candidate => !visited.has(candidate))
    }
  }
  const total = Math.max(ordered.reduce((sum, edge) => sum + edge[0].distanceTo(edge[1]), 0), .001)
  const positions: number[] = [], distances: number[] = []
  let distance = 0
  ordered.forEach(edge => {
    positions.push(...edge[0].toArray(), ...edge[1].toArray())
    distances.push(distance / total)
    distance += edge[0].distanceTo(edge[1])
    distances.push(distance / total)
  })
  const geometry = new BufferGeometry()
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3))
  geometry.setAttribute("path", new BufferAttribute(new Float32Array(distances), 1))
  return geometry
}
function ContourLight({ model, time, preset }: {
  model: Group; time: React.MutableRefObject<number>; preset: MaterialPreset
}) {
  const geometry = useMemo(() => contourGeometry(model), [model])
  const uniforms = useMemo(() => ({
    uTime: { value: 0 }, uColor: { value: new Color(preset.accent) },
  }), [])
  useEffect(() => () => geometry.dispose(), [geometry])
  useFrame(() => {
    uniforms.uTime.value = time.current
    uniforms.uColor.value.set(preset.accent)
  }, -2)
  return (
    <lineSegments renderOrder={1}>
      <primitive object={geometry} attach="geometry" dispose={null} />
      <shaderMaterial uniforms={uniforms} transparent depthWrite={false}
        blending={AdditiveBlending} toneMapped={false}
        vertexShader={`
          attribute float path; varying float vPath;
          void main() { vPath = path;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position * 1.003, 1.0); }
        `}
        fragmentShader={`
          uniform float uTime; uniform vec3 uColor; varying float vPath;
          void main() {
            float phase = fract(vPath - uTime * 0.13);
            float pulse = pow(1.0 - phase, 36.0);
            gl_FragColor = vec4(uColor * (1.0 + pulse * 3.0), .07 + pulse * .85);
            #include <colorspace_fragment>
          }
        `} />
    </lineSegments>
  )
}


function ReflectionStage({mode,angle,time,active,preset,pitch}:{
 mode:SavantMarkMode;angle:React.MutableRefObject<number>;time:React.MutableRefObject<number>
 active:boolean;preset:MaterialPreset;pitch:number
}){
 return <ReflectionCapture mode={mode} active={active} version={preset.id}>
  <mesh scale={16}>
   <sphereGeometry args={[1,32,16]}/>
   <meshBasicMaterial color="#080b10" side={BackSide} toneMapped={false}/>
  </mesh>
  <ReflectionLighting time={time} preset={preset}/>
  <RippleFilaments time={time} preset={preset}/>
  <CinematicParticles mode={mode} time={time} preset={preset}
   moving={active} reflection angle={angle} pitch={pitch}/>
 </ReflectionCapture>
}

function MarkScene({ mode, active, reducedMotion, preset, interaction, revision }: MarkSceneProps) {
  const gltf = useGLTF(assetUrl)
  const group = useRef<Group>(null)
  const shadowGroup = useRef<Group>(null)
  const shadowReceiver = useRef<Mesh>(null)
  const angle = useRef(0)
  const { invalidate, scene, camera, size } = useThree()
  const animationTime = useRef(0)
  const cameraHome = useRef(4)
  const angularSpeed = useRef(fullTurn/revolutionSeconds)
  const pinkLight = useRef<PointLight>(null)
  const goldLight = useRef<PointLight>(null)
  const rimLight = useRef<PointLight>(null)
  const effectUniforms = useMemo<EffectUniforms>(() => ({
    uSavantTime: { value: 0 }, uSavantGlitch: { value: 0 },
    uSavantStyle: { value: 0 }, uSavantAccent: { value: new Color(effectsPalette.gold) },
    uAccent2: { value: new Color("#dce6ef") }, uTextureScale: { value: 17 },
    uRelief: { value: .035 }, uGlow: { value: .16 },
  }), [])
  const receiver = useMemo(() => shadowReceiverMaterial(), [])
  const { model, materials, depthMaterials, bounds } = useMemo(
    () => prepareModel(gltf.scene, effectUniforms), [gltf.scene, effectUniforms],
  )


  useLayoutEffect(() => {
    if (!(camera instanceof PerspectiveCamera) || bounds.isEmpty()) return
    const extent = bounds.getSize(new Vector3())
    // Fit every horizontal orientation, including the model's thickness.
    const width = Math.hypot(extent.x, extent.z)
    const nominalHeight = Math.max(size.height - 32, 1)
    const nominalWidth = Math.max(size.width - 50, 1)
    const aspect = Math.max(nominalWidth / nominalHeight, 0.1)
    const visibleHeight = Math.max(extent.y, width / aspect) * 1.1
    camera.position.set(0, 0,
      (visibleHeight / (2 * Math.tan(MathUtils.degToRad(camera.fov / 2))) +
      width / 2) * size.height / nominalHeight)
    // Extra 50 CSS pixels at right are reserved for the projected shadow.
    camera.setViewOffset(size.width, size.height, 25, 16, size.width, size.height)
    cameraHome.current = camera.position.z
    camera.lookAt(0, 0, 0)
    camera.updateProjectionMatrix()
    invalidate()
  }, [bounds, camera, size.width, size.height, invalidate])

  useEffect(() => {
    for (const material of materials) {
      applyAppearance(material,preset)
    }
    effectUniforms.uSavantStyle.value = preset.style
    effectUniforms.uSavantAccent.value.set(preset.accent)
    effectUniforms.uAccent2.value.set(preset.accent2)
    effectUniforms.uTextureScale.value = preset.textureScale
    effectUniforms.uRelief.value = preset.relief
    effectUniforms.uGlow.value = preset.glow
    receiver.opacity = preset.scene.shadow
    model.traverse(object=>{
      if(object instanceof Mesh) object.castShadow =
        preset.optics.opacity === 1 && preset.optics.transmission < .8
    })
    invalidate()
  }, [preset, materials, effectUniforms, receiver, invalidate, model])

  useEffect(() => { invalidate() }, [active, reducedMotion, revision, invalidate])

  useEffect(() => () => {
    for (const material of materials) material.dispose()
    for (const material of depthMaterials) material.dispose()
    receiver.dispose()
  }, [materials, depthMaterials, receiver])

  useFrame((_, delta) => {
    if (!group.current) return
    if (active && !reducedMotion) {
      // Bound resume deltas so returning to a tab never jumps the logo.
      const dt=Math.min(Math.max(delta,0),.1)
      const targetSpeed=interaction.current.dragging?0:
        fullTurn/revolutionSeconds*(1+glitchAmount(animationTime.current)*3.5)
      angularSpeed.current=damp(angularSpeed.current,targetSpeed,8,dt)
      animationTime.current+=dt
      if(!interaction.current.dragging)interaction.current.yaw+=angularSpeed.current*dt
      angle.current = interaction.current.yaw % fullTurn
      invalidate()
    }
    effectUniforms.uSavantTime.value = animationTime.current
    effectUniforms.uSavantGlitch.value =
      active && !reducedMotion ? glitchAmount(animationTime.current) : 0
    const time = animationTime.current
    if (pinkLight.current) {
      pinkLight.current.position.set(Math.sin(time * 2.1) * 2.1,
        Math.cos(time * 1.6) * 1.5, 1.7 + Math.cos(time * 2.1) * 1.1)
      pinkLight.current.intensity = damp(pinkLight.current.intensity,reducedMotion?4:
        (6+Math.pow(.5+.5*Math.sin(time*2.1),6)*10+
         effectUniforms.uSavantGlitch.value*4)*preset.scene.energy,6,delta)
    }
    if (rimLight.current) {
      const phase = time * (2.8 + preset.scene.drift)
      rimLight.current.position.set(
        Math.cos(phase) * 1.65,
        Math.sin(phase * 0.79) * 1.45,
        0.75 + Math.sin(phase * 1.13) * 0.65,
      )
      const glint = Math.pow(Math.max(0, Math.sin(phase * 2.1)), 12)
      rimLight.current.intensity = damp(
        rimLight.current.intensity,
        (2.5 + glint * 14 + effectUniforms.uSavantGlitch.value * 9) * preset.scene.energy,
        9, delta,
      )
    }
    if (goldLight.current) {
      goldLight.current.position.set(Math.cos(time * 1.8) * 2,
        Math.sin(time * 2.3) * 1.7, 1.9 + Math.sin(time * 1.8))
      goldLight.current.intensity = damp(goldLight.current.intensity,reducedMotion?4:
        (7+Math.pow(.5+.5*Math.cos(time*1.8),6)*9+
         effectUniforms.uSavantGlitch.value*3)*preset.scene.energy,6,delta)
    }
    angle.current = interaction.current.yaw % fullTurn
    const tremor=interaction.current.dragging?0:effectUniforms.uSavantGlitch.value
    // Three non-harmonic oscillators keep the distortion visibly irregular.
    // The receiver follows the same displacement rather than trembling independently.
    const jitterX=(Math.sin(time*97)+.55*Math.sin(time*173+1.4))* .032*tremor
    const jitterY=(Math.sin(time*113+1.7)+.45*Math.sin(time*211))* .027*tremor
    const jitterZ=Math.sin(time*139+.6)*.022*tremor
    group.current.position.set(jitterX,jitterY,jitterZ)
    group.current.rotation.set(interaction.current.pitch+Math.sin(time*83)*.024*tremor,
      angle.current+Math.sin(time*149)*.028*tremor,
      Math.sin(time*71)*.038*tremor)
    if (shadowGroup.current) {
      shadowGroup.current.position.set(jitterX*.78,jitterY*.72+.12*tremor,jitterZ*.2)
      shadowGroup.current.rotation.z=group.current.rotation.z*.65
    }
    if (shadowReceiver.current) {
      shadowReceiver.current.scale.set(1.12+Math.abs(jitterX)*.9,
        1.32+Math.abs(jitterY)*.7,1)
    }
    if (camera instanceof PerspectiveCamera) {
      const local = time % 14
      const perspective = active && !reducedMotion && !interaction.current.dragging &&
        local > 8 && local < 12 ? Math.sin((local - 8) / 4 * Math.PI) ** 2 : 0
      camera.position.set(Math.sin(time * .8) * .36 * perspective,
        Math.cos(time * .6) * .16 * perspective,
        cameraHome.current * (1 - perspective * .035))
      camera.lookAt(0, 0, 0)
    }
    // Keep the probe aligned with real particle positions; stage ribbons
    // animate internally rather than rotating captured particle reflections.
    scene.environmentRotation.set(0, 0, 0)

  }, -3)

  return (
    <>
      <AtmosphereGlow time={animationTime} preset={preset}/>
      <ambientLight intensity={0.08} />
      <directionalLight color="#f4f7fa" intensity={3.2} position={[-3, 3.2, 3]}
        castShadow shadow-mapSize-width={mode === "header" ? 512 : 1024}
        shadow-mapSize-height={mode === "header" ? 512 : 1024}
        shadow-camera-left={-2} shadow-camera-right={2}
        shadow-camera-top={2} shadow-camera-bottom={-2}
        shadow-camera-near={0.1} shadow-camera-far={12}
        shadow-bias={-0.0002} shadow-normalBias={0.02} shadow-radius={3} />
      <directionalLight color={preset.accent2} intensity={1.8} position={[3, 1, -3]} />
      <directionalLight color="#899198" intensity={1} position={[-2, -3, -2]} />
      <ReflectionStage mode={mode} angle={angle} time={animationTime}
        active={active && !reducedMotion} preset={preset} pitch={interaction.current.pitch} />

      <pointLight ref={pinkLight} color={preset.accent2} intensity={0}
        distance={7} decay={2} />
      <pointLight ref={goldLight} color={preset.accent} intensity={0}
        distance={7} decay={2} />
      <pointLight ref={rimLight} color={preset.accent2} intensity={0}
        distance={5.5} decay={2} />
      <group ref={shadowGroup}>
        <mesh ref={shadowReceiver} position={[0.16, 0.38, -1.35]} scale={[1.12, 1.32, 1]} receiveShadow>
          <planeGeometry args={[5, 5]} />
          <primitive object={receiver} attach="material" dispose={null} />
        </mesh>
      </group>
      <CinematicParticles mode={mode} time={animationTime}
        preset={preset} moving={active && !reducedMotion} angle={angle} pitch={interaction.current.pitch} />
      <group ref={group}>
        <primitive object={model} dispose={null} />
        <PixelFragments model={model} mode={mode} uniforms={effectUniforms} preset={preset} />
        <ContourLight model={model} time={animationTime} preset={preset} />
      </group>
    </>
  )
}

function MarkFallback({
  mode,
}: {
  mode: SavantMarkMode
}) {
  return (
    <div
      className={
        "savant-mark__fallback " +
        `savant-mark__fallback--${mode}`
      }
      aria-hidden="true"
    >
      s
    </div>
  )
}


class SavantMarkBoundary
  extends React.Component<
    {
      mode: SavantMarkMode
      children: React.ReactNode
    },
    {
      failed: boolean
    }
  > {
  state = {
    failed: false,
  }

  static getDerivedStateFromError() {
    return {
      failed: true,
    }
  }

  componentDidCatch(
    error: unknown,
  ) {
    console.error(
      "savant mark failed to load",
      error,
    )
  }

  render() {
    if (
      this.state.failed
    ) {
      return (
        <MarkFallback
          mode={
            this.props.mode
          }
        />
      )
    }

    return this.props.children
  }
}


export default function SavantMark({
  mode = "header",
  state = "idle",
  className = "",
  label = "savant",
  progress,
  active = true,
}: SavantMarkProps) {
  const reducedMotion = useReducedMotion()
  const root = useRef<HTMLDivElement>(null)
  const visible = useAnimationVisibility(root)
  const animationActive = active && visible
  const { preset, choose } = useMaterialPreset()
  const interaction = useRef<Interaction>({ yaw: 0, pitch: 0, dragging: false })
  const pointer = useRef<{ id: number; x: number; y: number } | null>(null)
  const [revision, setRevision] = useState(0)
  const [header, setHeader] = useState<HTMLElement | null>(null)
  useEffect(() => {
    setHeader(mode === "header" ? root.current?.closest<HTMLElement>("header.workstation-topbar") || null : null)
  }, [mode])
  const release = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (pointer.current?.id !== event.pointerId) return
    pointer.current = null
    interaction.current.dragging = false
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    setRevision(value => value + 1)
  }
  const selector = (
    <label className="savant-mark__material-control">
      <span>surface laboratory</span>
      <select aria-label="savant logo and particle material" title={preset.description} value={preset.id}
        onChange={event => choose(event.target.value)}>
        {materialPresets.map(option => <option key={option.id}
          value={option.id} title={option.description}>{option.name}</option>)}
      </select>
    </label>
  )

  const progressValue =
    typeof progress ===
      "number"
      ? MathUtils.clamp(
          progress,
          0,
          1,
        )
      : undefined

  return (
    <div
      ref={root}
      className={[
        "savant-mark",
        `savant-mark--${mode}`,
        `savant-mark--${state}`,
        animationActive
          ? "is-active"
          : "is-resting",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      data-savant-state={
        state
      }
      role={mode === "preloader" ? "status" : "group"}
      aria-label={
        mode ===
        "preloader"
          ? `${label} loading`
          : label
      }
    >


      <div className="savant-mark__gleam" aria-hidden="true"
        style={{ background: `radial-gradient(ellipse at 44% 40%, ${preset.accent}26, ${preset.accent2}10 42%, transparent 75%)` }} />
      <button type="button" className="savant-mark__drag"
        aria-label="Rotate savant logo. Drag or use arrow keys; release to resume rotation."
        title="Drag to rotate · arrow keys to turn · Home to reset"
        onPointerDown={event => {
          if (event.button !== 0 || pointer.current) return
          event.stopPropagation()
          pointer.current = { id: event.pointerId, x: event.clientX, y: event.clientY }
          interaction.current.dragging = true
          event.currentTarget.setPointerCapture(event.pointerId)
          setRevision(value => value + 1)
        }}
        onPointerMove={event => {
          const last = pointer.current
          if (!last || last.id !== event.pointerId) return
          const scale = fullTurn / Math.max(event.currentTarget.clientWidth * 2, 1)
          interaction.current.yaw += (event.clientX - last.x) * scale
          interaction.current.pitch = MathUtils.clamp(interaction.current.pitch +
            (event.clientY - last.y) * scale, -.65, .65)
          last.x = event.clientX; last.y = event.clientY
          setRevision(value => value + 1)
        }}
        onPointerUp={release} onPointerCancel={release} onLostPointerCapture={release}
        onKeyDown={event => {
          const changes: Record<string, [number, number]> = {
            ArrowLeft: [-.15, 0], ArrowRight: [.15, 0],
            ArrowUp: [0, -.12], ArrowDown: [0, .12],
          }
          if (event.key === "Home") {
            interaction.current.yaw = 0; interaction.current.pitch = 0
          } else if (changes[event.key]) {
            interaction.current.yaw += changes[event.key][0]
            interaction.current.pitch = MathUtils.clamp(interaction.current.pitch +
              changes[event.key][1], -.65, .65)
          } else return
          event.preventDefault()
          setRevision(value => value + 1)
        }} />
      {mode === "header" && (header ? createDomPortal(selector, header) : selector)}

      <div
        className="savant-mark__viewport"
      >
        <SavantMarkBoundary
          mode={mode}
        >
          <Canvas
            frameloop="demand"
            shadows="soft"
            dpr={[1, 2]}
            gl={{
              alpha: true,
              antialias: true,
              powerPreference:
                "high-performance",
            }}
            camera={{
              position: [
                0,
                0,
                3.15,
              ],
              fov: 31,
              near: 0.1,
              far: 20,
            }}
            onCreated={({
              gl,
            }) => {
              gl.setClearColor(0x000000, 0)
              gl.toneMapping = ACESFilmicToneMapping
              gl.toneMappingExposure = 1.05
            }}
          >
            <Suspense
              fallback={null}
            >
              <MarkScene
                mode={mode}
                state={state}
                preset={preset}
                interaction={interaction}
                revision={revision}
                active={animationActive}
                reducedMotion={
                  reducedMotion
                }
              />
            </Suspense>
          </Canvas>
        </SavantMarkBoundary>
      </div>



      {mode ===
        "preloader" && (
        <div
          className="savant-mark__preloader-copy"
        >
          <span>
            {label}
          </span>

          <span
            className="savant-mark__preloader-state"
          >
            {state}
          </span>

          {progressValue !==
            undefined && (
            <div
              className="savant-mark__progress"
              aria-hidden="true"
            >
              <i
                style={{
                  transform:
                    `scaleX(${progressValue})`,
                }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}


useGLTF.preload(
  assetUrl,
)
