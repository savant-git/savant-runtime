import React, { Suspense, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { createPortal as createDomPortal } from "react-dom"
import { Canvas, createPortal, useFrame, useThree } from "@react-three/fiber"
import { useGLTF } from "@react-three/drei"
import { ACESFilmicToneMapping, AdditiveBlending, BackSide, Box3, Color, CubeCamera, BufferGeometry, DynamicDrawUsage, Group, HalfFloatType, InstancedMesh, MathUtils, Matrix4, Mesh, MeshDepthMaterial, MeshPhysicalMaterial, Object3D, PerspectiveCamera, PointLight, RGBADepthPacking, Scene, ShaderMaterial, ShadowMaterial, Vector3, WebGLCubeRenderTarget } from "three"
import { materialPresets, installSurface, applyAppearance, legacyPresetIds } from "./savant-surfaces"
import type { MaterialPreset, EffectUniforms } from "./savant-surfaces"
import { CinematicParticles } from "./savant-particles"
import { SavantContourLight } from "./savant-contour-light"
import { glitchState, damp } from "./savant-motion"
import { ReflectionLighting } from "./savant-atmosphere"
import { cleanLogoGeometry } from "./savant-geometry"
import {eventState} from "./savant-events"
import {SurfaceEvents} from "./savant-scene-effects"
import {SceneBudget} from "./savant-scene-budget"
import { getEffectBudget, type EffectBudget } from "./savant-effect-budgets"
import "./savant-mark.css"
import "../workspace/palaver-industrial.css"
import "./savant-hud.css"

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
  requestFrame: React.MutableRefObject<(()=>void)|null>
  reducedMotion: boolean
  gleamRef: React.RefObject<HTMLDivElement | null>
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
function prepareModel(source:Object3D,uniforms:EffectUniforms){
 const model=new Group(),clone=source.clone(true),geometries:BufferGeometry[]=[]
 const size=new Box3().setFromObject(source).getSize(new Vector3())
 const unit=Math.max(size.x,size.y,size.z,.0001)
 const material=new MeshPhysicalMaterial({name:"savant-single-pbr",color:"#eef5fb",
  metalness:1,roughness:.02,clearcoat:1,clearcoatRoughness:.025})
 const depth=new MeshDepthMaterial({depthPacking:RGBADepthPacking})
 installSurface(material,uniforms,unit);installSurface(depth,uniforms,unit)
 clone.traverse(object=>{
  if(!(object instanceof Mesh))return
  object.geometry=cleanLogoGeometry(object.geometry);geometries.push(object.geometry)
  object.material=material;object.customDepthMaterial=depth
  object.castShadow=true;object.receiveShadow=true
 })
 model.add(clone);model.updateMatrixWorld(true)
 const bounds=new Box3().setFromObject(model)
 if(!bounds.isEmpty()){
  const extent=bounds.getSize(new Vector3()),center=bounds.getCenter(new Vector3())
  const scale=2/Math.max(extent.x,extent.y,extent.z,.0001)
  model.scale.setScalar(scale);model.position.copy(center).multiplyScalar(-scale)
 }
 model.scale.z*=1.6;model.position.z*=1.6;model.updateMatrixWorld(true)
 return {model,materials:[material],depthMaterials:[depth],geometries,
  bounds:new Box3().setFromObject(model)}
}

/* Capture only the reflection stage and matching particle projections.
 * The logo is excluded, avoiding recursive self-reflections. */
function ReflectionCapture({ mode, active, children, version, effectBudget }: {
  mode: SavantMarkMode
  active: boolean
  children: React.ReactNode
  version: string
  effectBudget: EffectBudget
}) {
  const { gl, scene, invalidate } = useThree()
  const stage = useMemo(() => new Scene(), [])
  const capture = useMemo(() => {
    const target = new WebGLCubeRenderTarget(mode === "header" ? 256 : 512,
      { type: HalfFloatType, generateMipmaps: false })
    return { target, camera: new CubeCamera(0.05, 40, target) }
  }, [mode])
  const elapsed = useRef(1)
  const lastResolution = useRef(0)
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
    const interval = (frameCost.current > .024 ? .8 : .28) * Math.max(1, effectBudget.reflectionUpdateInterval)
    if (ready.current && (!active || elapsed.current < interval)) return
    const baseSize = mode === "header" ? 256 : 512
    const resolution = Math.max(64, Math.round(baseSize * Math.max(0.25, Math.min(1, effectBudget.reflectionResolution))))
    if (lastResolution.current !== resolution) {
      capture.target.setSize(resolution, resolution)
      lastResolution.current = resolution
    }
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

/* Surface-anchored, camera-depth-aware temporal glitch fragments.
 * Uses the existing model geometry and animation clock, with no readback or
 * persistent render targets. One instanced draw serves all depth strata. */
function PixelFragments({ model, mode, uniforms, preset }: {
  model: Group
  mode: SavantMarkMode
  uniforms: EffectUniforms
  preset: MaterialPreset
}) {
  const mesh = useRef<InstancedMesh>(null)
  const matrix = useMemo(() => new Matrix4(), [])
  const cameraPosition = useMemo(() => new Vector3(), [])
  const worldPoint = useMemo(() => new Vector3(), [])
  const viewDirection = useMemo(() => new Vector3(), [])
  const modelWorld = useMemo(() => new Matrix4(), [])
  const samples = useMemo(() => {
    model.updateWorldMatrix(true, true)
    const parentInverse = model.parent
      ? new Matrix4().copy(model.parent.matrixWorld).invert()
      : new Matrix4()
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
  useFrame(({ camera }) => {
    const instance = mesh.current
    if (!instance) return
    const amount = uniforms.uSavantGlitch.value
    instance.visible = amount > 0.05
    if (!instance.visible) return

    model.updateWorldMatrix(true, false)
    modelWorld.copy(model.matrixWorld)
    camera.getWorldPosition(cameraPosition)
    const tick = Math.floor(uniforms.uSavantTime.value * 48)
    const burst = Math.floor(tick / 7)
    const phase = tick % 7
    let drawn = 0
    for (let index = 0; index < samples.length; index++) {
      const point = samples[index]
      worldPoint.copy(point).applyMatrix4(modelWorld)
      viewDirection.copy(cameraPosition).sub(worldPoint)
      const depth = Math.max(0.01, viewDirection.length())
      viewDirection.multiplyScalar(1 / depth)

      // Stable per-burst sampling prevents flicker from becoming white noise.
      const seed = Math.sin((index + 1) * 127.1 + burst * 311.7) * 43758.5453
      const random = seed - Math.floor(seed)
      const stratum = index % 3
      const threshold = stratum === 0 ? 0.26 : stratum === 1 ? 0.49 : 0.7
      if (random > threshold * Math.min(1, amount * 1.7)) continue

      // Depth strata shift at different rates, producing actual parallax.
      const depthFactor = Math.min(1.7, 4 / depth)
      const stepped = Math.sin(index * 17.31 + burst * 2.7)
      const envelope = Math.sin(Math.PI * phase / 7)
      const displacement = amount * (0.1 + 0.13 * stratum) * depthFactor * envelope
      const size = (0.012 + (index % 4) * 0.004) * amount
      matrix.makeScale(size * (2 + stratum * 1.5), size * (1 + stratum * .2), size * .65)
      matrix.setPosition(
        point.x + stepped * displacement,
        point.y + Math.sin(index * 4.3 + burst) * displacement * .4,
        point.z + Math.cos(index * 7.1 + burst) * displacement * .55
          + (stratum - 1) * .08 * amount
      )
      instance.setMatrixAt(drawn++, matrix)
    }
    instance.count = drawn
    instance.instanceMatrix.needsUpdate = true
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
function ReflectionStage({mode,angle,time,active,preset,pitch,effectBudget}:{
 mode:SavantMarkMode;angle:React.MutableRefObject<number>;time:React.MutableRefObject<number>
 active:boolean;preset:MaterialPreset;pitch:number|React.MutableRefObject<{pitch:number}>;effectBudget:EffectBudget
}){
 return <ReflectionCapture mode={mode} active={active} version={preset.id} effectBudget={effectBudget}>
  <mesh scale={16}>
   <sphereGeometry args={[1,32,16]}/>
   <meshBasicMaterial color="#080b10" side={BackSide} toneMapped={false}/>
  </mesh>
  <ReflectionLighting time={time} preset={preset}/>
  <MovingReflectionForms time={time} preset={preset} active={active}/>
  <CinematicParticles mode={mode} time={time} preset={preset}
   moving={active} reflection angle={angle} pitch={pitch} effectBudget={effectBudget}/>
 </ReflectionCapture>
}

/* Color-matched moving reflector geometry captured in the environment map.
 * No recursive logo capture and no independent animation clock. */
function MovingReflectionForms({time,preset,active}:{
  time:React.MutableRefObject<number>;preset:MaterialPreset;active:boolean
}) {
  const orbit=useRef<Group>(null)
  useFrame(()=>{
    if (!orbit.current || !active) return
    const t=time.current
    orbit.current.rotation.set(Math.sin(t*.17)*.18,t*.31,Math.cos(t*.23)*.14)
    orbit.current.position.set(Math.sin(t*.29)*.2,Math.cos(t*.21)*.14,0)
  })
  return <group ref={orbit}>
    <mesh position={[2.4,.8,-1.3]} rotation={[.35,.5,.25]}>
      <torusGeometry args={[.9,.085,10,72]}/>
      <meshBasicMaterial color={preset.accent} toneMapped={false}/>
    </mesh>
    <mesh position={[-2.2,-.9,1.2]} rotation={[.9,.3,.4]}>
      <torusGeometry args={[.65,.06,10,64]}/>
      <meshBasicMaterial color={preset.accent2} toneMapped={false}/>
    </mesh>
    <mesh position={[1.4,-2.1,-1.8]} rotation={[.24,.65,-.48]}>
      <boxGeometry args={[1.8,.95,.045]}/>
      <meshBasicMaterial color={preset.accent2} toneMapped={false}/>
    </mesh>
    <mesh position={[-2.8,1.7,-.8]} rotation={[.45,-.3,.55]}>
      <cylinderGeometry args={[.38,.65,2.4,28,1,true]}/>
      <meshBasicMaterial color={preset.accent} toneMapped={false} side={2}/>
    </mesh>
    <mesh position={[0,-2.4,2.2]} rotation={[.4,0,.24]}>
      <planeGeometry args={[3.6,.28]}/>
      <meshBasicMaterial color={preset.particle} toneMapped={false} side={2}/>
    </mesh>
    <mesh position={[.4,2.6,-1.1]} rotation={[.4,1.1,.2]}>
      <planeGeometry args={[1.8,.12]}/>
      <meshBasicMaterial color={preset.particle} toneMapped={false} side={2}/>
    </mesh>
  </group>
}

/* Camera-facing optical ghosts driven by the same orbit clock as the rim light.
 * These are intentionally screen-space-style flare sprites, not simulated optics. */
function OrbitingLensFlares({ time, preset, reducedMotion }: {
  time: React.MutableRefObject<number>
  preset: MaterialPreset
  reducedMotion: boolean
}) {
  const sprites = useRef<Array<Mesh | null>>([])
  const shaderUniforms = useMemo(() => ({
    uColor: { value: new Color(preset.accent) },
    uSecondary: { value: new Color(preset.accent2) },
    uEnergy: { value: preset.scene.energy },
    uTime: { value: 0 },
  }), [])
  useFrame(({ camera }) => {
    const t = reducedMotion ? 0 : time.current
    shaderUniforms.uTime.value = t
    shaderUniforms.uColor.value.set(preset.accent)
    shaderUniforms.uSecondary.value.set(preset.accent2)
    shaderUniforms.uEnergy.value = preset.scene.energy
    const phase = t * (2.8 + preset.scene.drift)
    const x = Math.cos(phase) * 1.65
    const y = Math.sin(phase * .79) * 1.45
    const z = .75 + Math.sin(phase * 1.13) * .65
    sprites.current.forEach((sprite, index) => {
      if (!sprite) return
      const fraction = index === 0 ? 1 : index === 1 ? -.38 : -.8
      sprite.position.set(x * fraction, y * fraction, z - index * .13)
      sprite.quaternion.copy(camera.quaternion)
      const scale = (index === 0 ? .8 : index === 1 ? .32 : .55) *
        (1 + .12 * Math.sin(t * 2.7 + index))
      sprite.scale.setScalar(scale)
    })
  }, -2)
  return <group>
    {[0, 1, 2].map(index => <mesh
      key={index}
      ref={value => { sprites.current[index] = value }}
      renderOrder={3}
      frustumCulled={false}
    >
      <planeGeometry args={[1, 1]} />
      <shaderMaterial
        uniforms={shaderUniforms}
        transparent
        depthWrite={false}
        depthTest={true}
        blending={AdditiveBlending}
        toneMapped={false}
        vertexShader={`
          varying vec2 vUv;
          void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}
        `}
        fragmentShader={`
          varying vec2 vUv;
          uniform vec3 uColor,uSecondary;
          uniform float uTime,uEnergy;
          void main(){
            vec2 p=(vUv-.5)*2.0;
            float r=length(p);
            float core=exp(-r*r*70.0);
            float halo=exp(-pow(r-.48,2.0)*380.0)*.2;
            float horizontal=exp(-p.y*p.y*1100.0)*exp(-abs(p.x)*3.5)*.46;
            float vertical=exp(-p.x*p.x*1200.0)*exp(-abs(p.y)*4.0)*.21;
            float diagonal=exp(-pow(p.y-p.x*.42,2.0)*950.0)*exp(-r*4.0)*.12;
            float pulse=.76+.24*sin(uTime*3.1);
            float strength=(core+halo+horizontal+vertical+diagonal)*pulse;
            vec3 tint=mix(uColor,uSecondary,smoothstep(.15,.7,r));
            gl_FragColor=vec4(tint*strength*min(uEnergy,2.5),clamp(strength*.6,0.0,.8));
            #include <colorspace_fragment>
          }
        `}
      />
    </mesh>)}
  </group>
}

/* One bounded procedural environment: five independently animated visual layers
 * whose composition and palette change with the selected artist treatment.
 * Geometry stays outside the logo and is never used to deform the GLB. */
function ArtistAtmosphere({time,preset,moving}: {
 time:React.MutableRefObject<number>;preset:MaterialPreset;moving:boolean
}) {
 const uniforms=useMemo(()=>({
  uTime:{value:0},uStyle:{value:0},uEnergy:{value:1},
  uColor:{value:new Color()},uSecond:{value:new Color()},
 }),[])
 useFrame(()=>{
  uniforms.uTime.value=moving?time.current:0
  uniforms.uStyle.value=preset.style
  uniforms.uEnergy.value=preset.scene.energy
  uniforms.uColor.value.set(preset.accent)
  uniforms.uSecond.value.set(preset.accent2)
 },-2)
 return <mesh position={[0,0,-2.7]} renderOrder={-3} frustumCulled={false}>
  <planeGeometry args={[9,9]}/>
  <shaderMaterial uniforms={uniforms} transparent depthWrite={false} depthTest={false}
   blending={AdditiveBlending} toneMapped={false}
   vertexShader={`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`}
   fragmentShader={`
    varying vec2 vUv;
    uniform float uTime,uStyle,uEnergy;
    uniform vec3 uColor,uSecond;
    float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
     return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+1.),f.x),f.y);}
    void main(){
     vec2 p=(vUv-.5)*2.;float t=uTime;
     float style=uStyle;
     float scale=1.4+mod(style,5.)*.68;
     float a=style*.61803398875;
     mat2 rotation=mat2(cos(a),-sin(a),sin(a),cos(a));
     vec2 q=rotation*p;
     // Layer 1: drifting light shafts with deterministic orientation.
     float shafts=pow(max(0.,sin(q.x*(4.+mod(style,7.))+t*(.12+mod(style,3.)*.07))),8.);
     // Layer 2: slow layered fog, moving in opposing directions.
     float fog=noise(q*scale+vec2(t*.07,-t*.035))*.65+
       noise(q*scale*2.7+vec2(-t*.11,t*.06))*.35;
     // Layer 3: fine etched, halftone, woven or gridded interference.
     float pattern=abs(sin(q.x*(18.+mod(style,6.)*9.))*cos(q.y*(12.+mod(style,5.)*7.)));
     pattern=pow(pattern,2.+mod(style,4.));
     // Layer 4: two asymmetric orbital caustics.
     float orbit=exp(-length(p-vec2(sin(t*.23+a)*.48,cos(t*.19+a)*.34))*5.);
     orbit+=.6*exp(-length(p-vec2(cos(t*.17-a)*.62,sin(t*.27-a)*.39))*8.);
     // Layer 5: sweeping diffraction rings, phase and spacing vary by treatment.
     float rings=pow(max(0.,cos(length(q*vec2(1.,1.+mod(style,4.)*.3))*
       (12.+mod(style,8.)*3.)-t*(.3+mod(style,3.)*.15))),12.);
     float vignette=pow(max(0.,1.-dot(p,p)*.5),2.2);
     float intensity=(shafts*.13+fog*.15+pattern*.055+orbit*.22+rings*.085)*vignette;
     float pulse=.88+.12*sin(t*(.5+mod(style,5.)*.1)+a);
     vec3 color=mix(uColor,uSecond,clamp(fog*.7+orbit*.2,0.,1.));
     gl_FragColor=vec4(color*intensity*pulse*min(uEnergy,2.5),clamp(intensity*.46,0.,.32));
    }
   `}/>
 </mesh>
}


function MarkScene({ mode, active, reducedMotion, preset, interaction, revision,requestFrame,gleamRef }: MarkSceneProps) {
  const [effectBudget, setEffectBudget] = useState<EffectBudget>(() => getEffectBudget("cinematic"))
  const gltf = useGLTF(assetUrl)

  const group = useRef<Group>(null)
  const shadowGroup = useRef<Group>(null)
  const shadowReceiver = useRef<Mesh>(null)
  const angle = useRef(0)
  const { invalidate, scene, camera, size } = useThree()
  useEffect(()=>{requestFrame.current=invalidate;return()=>{requestFrame.current=null}},[requestFrame,invalidate])
  const animationTime = useRef(0)
  const cameraHome = useRef(4)
  const angularSpeed = useRef(fullTurn/revolutionSeconds)
  const cameraPerspective = useRef(0)
  const pinkLight = useRef<PointLight>(null)
  const goldLight = useRef<PointLight>(null)
  const rimLight = useRef<PointLight>(null)
  const effectUniforms = useMemo<EffectUniforms>(() => ({
    uEvent:{value:0},uEventProgress:{value:0},uSavantTime: { value: 0 }, uSavantGlitch: { value: 0 }, uInteraction:{value:0},
    uSavantStyle: { value: 0 }, uSavantAccent: { value: new Color(effectsPalette.gold) },
    uAccent2: { value: new Color("#dce6ef") }, uTextureScale: { value: 17 },
    uRelief: { value: .035 }, uGlow: { value: .16 },
  }), [])
  const receiver = useMemo(() => shadowReceiverMaterial(), [])
  const { model, materials, depthMaterials, geometries, bounds } = useMemo(
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
    for(const geometry of geometries) geometry.dispose()
    receiver.dispose()
  }, [materials, depthMaterials, geometries, receiver])

  useFrame((_, delta) => {
    if (!group.current) return
    if (active && !reducedMotion) {
      // Bound resume deltas so returning to a tab never jumps the logo.
      const dt=Math.min(Math.max(delta,0),.1)
      const targetSpeed=interaction.current.dragging?0:
        fullTurn/revolutionSeconds
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
    const event=eventState(time,preset.style)
    if (gleamRef.current) gleamRef.current.style.setProperty("--savant-lightning", "0")
    effectUniforms.uEvent.value=active&&!reducedMotion?event.strength:0
    effectUniforms.uEventProgress.value=event.progress
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
    if(!interaction.current.dragging){
      interaction.current.pitch=damp(interaction.current.pitch,0,5,delta)
      if(Math.abs(interaction.current.pitch)<.0001)interaction.current.pitch=0
    }
    effectUniforms.uInteraction.value=damp(effectUniforms.uInteraction.value,
      interaction.current.dragging?1:0,interaction.current.dragging?8:3,delta)
    angle.current = interaction.current.yaw % fullTurn
    group.current.position.set(0,0,0)
    group.current.rotation.set(interaction.current.pitch,angle.current,0)
    if (camera instanceof PerspectiveCamera) {
      const local = time % 14
      const targetPerspective = active && !reducedMotion && !interaction.current.dragging &&
        local > 8 && local < 12 ? Math.sin((local - 8) / 4 * Math.PI) ** 2 : 0
      cameraPerspective.current=damp(cameraPerspective.current,targetPerspective,5,delta)
      const perspective=cameraPerspective.current
      camera.position.set(Math.sin(time * .8) * .72 * perspective,
        Math.cos(time * .6) * .28 * perspective,
        cameraHome.current * (1 - perspective * .065))
      camera.lookAt(0, 0, 0)
    }
    if(active && (Math.abs(interaction.current.pitch)>.0001||effectUniforms.uInteraction.value>.001))invalidate()
    // Keep the probe aligned with real particle positions; stage ribbons
    // animate internally rather than rotating captured particle reflections.
    scene.environmentRotation.set(0, 0, 0)

  }, -3)

  return (
    <>
      <SceneBudget active={active&&!reducedMotion} onEffectBudgetChange={setEffectBudget}/>
      <ArtistAtmosphere time={animationTime} preset={preset} moving={active&&!reducedMotion}/>
      <ambientLight intensity={0.08} />
      <directionalLight color="#f4f7fa" intensity={3.2} position={[-2.4, 1.8, 4]}
        castShadow shadow-mapSize-width={mode === "header" ? 512 : 1024}
        shadow-mapSize-height={mode === "header" ? 512 : 1024}
        shadow-camera-left={-2} shadow-camera-right={2}
        shadow-camera-top={2} shadow-camera-bottom={-2}
        shadow-camera-near={0.1} shadow-camera-far={12}
        shadow-bias={-0.0002} shadow-normalBias={0.02} shadow-radius={3} />
      <directionalLight color={preset.accent2} intensity={1.8} position={[3, 1, -3]} />
      <directionalLight color="#899198" intensity={1} position={[-2, -3, -2]} />
      <ReflectionStage mode={mode} angle={angle} time={animationTime}
        active={active && !reducedMotion} preset={preset} pitch={interaction} effectBudget={effectBudget} />

      <pointLight ref={pinkLight} color={preset.accent2} intensity={0}
        distance={7} decay={2} />
      <pointLight ref={goldLight} color={preset.accent} intensity={0}
        distance={7} decay={2} />
      <pointLight ref={rimLight} color={preset.accent2} intensity={0}
        distance={5.5} decay={2} />
      <group ref={shadowGroup}>
        <mesh ref={shadowReceiver} position={[0.1, 0.26, -.9]} scale={[1.12, 1.32, 1]} receiveShadow>
          <planeGeometry args={[5, 5]} />
          <primitive object={receiver} attach="material" dispose={null} />
        </mesh>
      </group>
      <OrbitingLensFlares time={animationTime} preset={preset} reducedMotion={reducedMotion} />
      <CinematicParticles mode={mode} time={animationTime}
        preset={preset} moving={active && !reducedMotion} angle={angle} pitch={interaction} effectBudget={effectBudget} />
      <group ref={group}>
        <primitive object={model} dispose={null} />
        <SavantContourLight time={animationTime} active={active && !reducedMotion} color={preset.accent} />
        <SurfaceEvents model={model} time={animationTime} preset={preset} moving={active&&!reducedMotion}/>
        <PixelFragments model={model} mode={mode} uniforms={effectUniforms} preset={preset} />

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
  const gleamRef = useRef<HTMLDivElement>(null)
  const visible = useAnimationVisibility(root)
  const animationActive = active && visible
  const { preset, choose } = useMaterialPreset()
  const interaction = useRef<Interaction>({ yaw: 0, pitch: 0, dragging: false })
  const pointer = useRef<{ id: number; x: number; y: number } | null>(null)
  const [revision, setRevision] = useState(0)
  const requestFrame=useRef<(()=>void)|null>(null)
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


      <div ref={gleamRef} aria-hidden="true" style={{display:"none"}} />
      <button type="button" className="savant-mark__drag" style={{touchAction:"none"}}
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
          requestFrame.current?.()
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
            dpr={[1, 1.75]}
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
                requestFrame={requestFrame}
                gleamRef={gleamRef}
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
	

