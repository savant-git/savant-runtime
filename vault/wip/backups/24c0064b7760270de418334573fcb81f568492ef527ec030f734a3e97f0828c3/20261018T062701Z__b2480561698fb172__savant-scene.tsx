import React,{useEffect,useLayoutEffect,useMemo,useRef,useState} from "react"
import {useFrame,useThree} from "@react-three/fiber"
import {Color,Group,MathUtils,Mesh,PerspectiveCamera,PointLight,Vector3} from "three"
import {useGLTF} from "@react-three/drei"
import {applyAppearance} from "./savant-surfaces"
import type {EffectUniforms} from "./savant-surfaces"
import type {MarkSceneProps} from "./savant-mark-types"
import {prepareModel} from "./savant-model"
import {shadowReceiverMaterial} from "./savant-shadow"
import {ArtistAtmosphere} from "./savant-atmosphere-layer"
import {SceneBudget} from "./savant-scene-budget"
import {getEffectBudget,type EffectBudget} from "./savant-effect-budgets"
import {SavantReflectionEnvironment} from "./savant-reflections"
import {CinematicParticles} from "./savant-particles"
import {SavantContourLight} from "./savant-contour-light"
import {damp,glitchState} from "./savant-motion"
import {eventState} from "./savant-events"
const assetUrl="/cinematic/savant_logo.glb",fullTurn=Math.PI*2,revolutionSeconds=8
const effectsPalette={pink:"#ff2f9d",gold:"#d6b45f"}
const glitchAmount=(time:number)=>glitchState(time).amount
export function MarkScene({ mode, active, reducedMotion, preset, interaction, revision,requestFrame,gleamRef,framingScale }: MarkSceneProps) {
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
    uSavantStyle: { value: preset.style }, uSavantAccent: { value: new Color(effectsPalette.gold) },
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
    const nominalHeight = Math.max(size.height - 32 * framingScale, 1)
    const nominalWidth = Math.max(size.width - 50 * framingScale, 1)
    const aspect = Math.max(nominalWidth / nominalHeight, 0.1)
    const visibleHeight = Math.max(extent.y, width / aspect) * 1.1
    camera.position.set(0, 0,
      (visibleHeight / (2 * Math.tan(MathUtils.degToRad(camera.fov / 2))) +
      width / 2) * size.height / nominalHeight)
    // Extra 50 CSS pixels at right are reserved for the projected shadow.
    camera.setViewOffset(size.width, size.height, 25 * framingScale, 16 * framingScale, size.width, size.height)
    cameraHome.current = camera.position.z
    camera.lookAt(0, 0, 0)
    camera.updateProjectionMatrix()
    invalidate()
  }, [bounds, camera, size.width, size.height, framingScale, invalidate])

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
        (2.8+Math.pow(.5+.5*Math.sin(time*2.1),6)*3+
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
        (1.8 + glint * 4 + effectUniforms.uSavantGlitch.value * 2) * preset.scene.energy,
        9, delta,
      )
    }
    if (goldLight.current) {
      goldLight.current.position.set(Math.cos(time * 1.8) * 2,
        Math.sin(time * 2.3) * 1.7, 1.9 + Math.sin(time * 1.8))
      goldLight.current.intensity = damp(goldLight.current.intensity,reducedMotion?4:
        (3.1+Math.pow(.5+.5*Math.cos(time*1.8),6)*3.5+
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
      <SavantReflectionEnvironment/>

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


      <group ref={group}>
        <primitive object={model} dispose={null} />
        <SavantContourLight time={animationTime} active={active && !reducedMotion} color="#e5ad39" model={model} glitch={effectUniforms.uSavantGlitch} />
        <CinematicParticles mode={mode} time={animationTime} preset={preset} moving={active && !reducedMotion} angle={angle} pitch={interaction} effectBudget={effectBudget} />



      </group>
    </>
  )
}
