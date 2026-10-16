import React, { useEffect, useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { AdditiveBlending, CatmullRomCurve3, Color, DoubleSide, Mesh, ShaderMaterial, TubeGeometry, Vector3, BufferGeometry, Float32BufferAttribute, MeshPhysicalMaterial, IcosahedronGeometry, PointLight } from "three"
import { glitchState } from "./savant-motion"
import { savantContour, savantContourFrontZ } from "./savant-contour-data"

const turnsPerSecond = 0.095
const wakeSeconds = 9.65
const orbit = (time: number) => ((time * turnsPerSecond) % 1 + 1) % 1

function ContourRunner({ time, active, color, direction, side }: {
  time: React.MutableRefObject<number>; active: boolean; color: string; side: 1 | -1
}) {
  const head = useRef<Mesh>(null)
  const curve = useMemo(() => new CatmullRomCurve3(
    savantContour.map(([x, y]) => new Vector3(x, y, side * (Math.abs(savantContourFrontZ) + .018))),
    true, "centripetal", .5,
  ), [side])
  const geometry = useMemo(() => new TubeGeometry(curve, 768, .024, 8, true), [curve])
  const material = useMemo(() => new ShaderMaterial({
    transparent: true, depthWrite: false, depthTest: true, side: DoubleSide,
    blending: AdditiveBlending, toneMapped: false,
    uniforms: {
      uTime: { value: 0 }, uActive: { value: 0 }, uColor: { value: new Color(color) },
      uDirection: { value: 1 }, uPhase: { value: 0 },
      uDuration: { value: wakeSeconds }, uGlitch: { value: 0 },
    },
    vertexShader: `varying vec2 vUv; varying vec3 vWorld; uniform float uTime,uGlitch;
      void main(){vUv=uv;vec3 p=position;
        float bands=floor(p.y*47.+uTime*37.);
        float burst=step(.48,fract(sin(bands*91.7+floor(uTime*44.))*43758.545));
        p.x+=uGlitch*burst*.19*sin(bands*3.1+uTime*53.);
        p.z+=uGlitch*burst*.10*cos(bands*2.7+uTime*41.);
        vWorld=p;gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.); }`,
    fragmentShader: `varying vec2 vUv; varying vec3 vWorld;
      uniform float uTime,uActive,uDirection,uPhase,uDuration;uniform vec3 uColor;
      void main(){
        float head=fract(uTime*${turnsPerSecond.toFixed(6)}*uDirection+uPhase);
        float distanceBehind=fract((head-vUv.x)*uDirection+1.);
        float age=distanceBehind/${turnsPerSecond.toFixed(6)};
        float fade=1.-smoothstep(.12,uDuration,age);
        float bloom=1.-smoothstep(0.,.06,age);
        float afterOne=smoothstep(.93,1.35,age);
        float edge=abs(vUv.y-.5)*2.;
        float vapor=sin(vUv.x*173.+uTime*1.3)*sin(vUv.x*97.-uTime*.8);
        float widening=mix(pow(1.-edge,1.3),pow(1.-edge,.32),afterOne);
        float diffusion=mix(1.,.45+.12*vapor,afterOne);
        float throb=1.25+.55*pow(.5+.5*sin(uTime*2.05),3.);
        float alpha=uActive*fade*widening*diffusion*(1.35+bloom*1.4)*throb;
        if(alpha<.006)discard;
        vec3 tint=mix(uColor,vec3(1.,.10,.47),smoothstep(3.8,uDuration,age));
        gl_FragColor=vec4(tint*5.9,clamp(alpha,0.,1.));
      }`,
  }), [])
  useEffect(() => { material.uniforms.uColor.value.set(color) }, [material, color])
  useEffect(() => () => { geometry.dispose(); material.dispose() }, [geometry, material])
  useFrame(() => {
    material.uniforms.uTime.value = time.current
    material.uniforms.uGlitch.value = glitchState(time.current).amount
    material.uniforms.uActive.value = active ? 1 : 0
    if (head.current) {
      head.current.position.copy(curve.getPointAt(orbit(time.current)))
      head.current.scale.setScalar(active ? 1 + .12 * Math.sin(time.current * 8) : .75)
      head.current.rotation.set(time.current*4.1, time.current*6.2, time.current*3.3)
      head.current.visible = active
    }
  })
  return <group>
    <mesh geometry={geometry} material={material} frustumCulled={false} />
    <mesh ref={head}>
      <icosahedronGeometry args={[.105, 0]} />
      <meshPhysicalMaterial color="#080b10" metalness={1} roughness={0.035} clearcoat={1} clearcoatRoughness={0.015} envMapIntensity={3.8} />
      <pointLight color={color} intensity={15} distance={1.7} decay={2} />
      <mesh scale={1.20}>
        <icosahedronGeometry args={[.105, 0]} />
        <meshBasicMaterial color={color} transparent opacity={0.23} toneMapped={false} depthWrite={false} />
      </mesh>
    </mesh>
  </group>
}

/** One source contour drives both faces and the synchronized cross-thickness links. */
function ContourCrossLinks({ time, active, color }: {
  time: React.MutableRefObject<number>; active: boolean; color: string
}) {
  const count = Math.max(1, Math.round(1 / (turnsPerSecond * .3)))
  const front = Math.abs(savantContourFrontZ) + .018
  const curve = useMemo(() => new CatmullRomCurve3(
    savantContour.map(([x,y]) => new Vector3(x,y,0)), true, "centripetal", .5
  ), [])
  const geometry = useMemo(() => {
    const points: number[] = []
    const phases: number[] = []
    const emit = (a: Vector3, b: Vector3, phase: number) => {
      points.push(a.x,a.y,a.z,b.x,b.y,b.z)
      phases.push(phase,phase)
    }
    // A pair of opposing diagonal windings forms a volumetric carbon weave.
    // Each .3-second station contributes four connected luminous strands.
    const strands = 5
    for (let i=0;i<count;i++) {
      const phase=i/count
      const p=curve.getPointAt(phase)
      const next=curve.getPointAt(((i+1)%count)/count)
      const tangent=curve.getTangentAt(phase).normalize()
      const across=new Vector3(-tangent.y,tangent.x,0).multiplyScalar(.038)
      for(let j=0;j<strands;j++) {
        const a=j/strands
        const b=(j+1)/strands
        const z0=-front+2*front*a
        const z1=-front+2*front*b
        const forward=new Vector3().copy(p).lerp(next,b)
        const backward=new Vector3().copy(next).lerp(p,b)
        emit(new Vector3(p.x,p.y,z0).addScaledVector(across,j%2?1:-1),
             new Vector3(forward.x,forward.y,z1).addScaledVector(across,j%2?-1:1),phase)
        emit(new Vector3(next.x,next.y,z0).addScaledVector(across,j%2?-1:1),
             new Vector3(backward.x,backward.y,z1).addScaledVector(across,j%2?1:-1),phase)
      }
    }
    const g=new BufferGeometry()
    g.setAttribute('position',new Float32BufferAttribute(points,3))
    g.setAttribute('aPhase',new Float32BufferAttribute(phases,1))
    return g
  },[curve,count,front])
  const material = useMemo(() => new ShaderMaterial({
    transparent:true,depthWrite:false,depthTest:true,blending:AdditiveBlending,
    toneMapped:false,
    uniforms:{uTime:{value:0},uActive:{value:0},uColor:{value:new Color(color)},uGlitch:{value:0}},
    vertexShader:`attribute float aPhase;varying float vPhase;uniform float uTime,uGlitch;
      void main(){vPhase=aPhase;vec3 p=position;
      float stripe=floor(p.y*41.+p.z*27.+uTime*32.);
      float noise=fract(sin(stripe*91.71+floor(uTime*39.))*43758.545);
      p.x+=uGlitch*step(.48,noise)*.22*sin(stripe*2.3+uTime*47.);
      p.y+=uGlitch*step(.65,noise)*.10*cos(stripe+uTime*57.);
      gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);}`,
    fragmentShader:`varying float vPhase;uniform float uTime,uActive,uGlitch;uniform vec3 uColor;
      void main(){float head=fract(uTime*${turnsPerSecond.toFixed(6)});
      float age=fract(head-vPhase+1.)/${turnsPerSecond.toFixed(6)};
      float fade=1.-smoothstep(.12,${wakeSeconds.toFixed(2)},age);
      float appear=smoothstep(0.,.11,age);
      float throb=1.25+.55*pow(.5+.5*sin(uTime*2.05),3.);
      float flicker=1.-uGlitch*.6*step(.57,fract(sin(vPhase*891.+floor(uTime*51.))*18753.));
      float alpha=uActive*appear*fade*throb*flicker;
      if(alpha<.006)discard;
      vec3 tint=mix(uColor,vec3(1.,.10,.47),smoothstep(3.8,${wakeSeconds.toFixed(2)},age));
      gl_FragColor=vec4(tint*6.4,clamp(alpha,0.,1.));}`,
  }),[color])
  useEffect(()=>()=>{geometry.dispose();material.dispose()},[geometry,material])
  useFrame(()=>{
    material.uniforms.uTime.value=time.current
    material.uniforms.uActive.value=active?1:0
    material.uniforms.uGlitch.value=glitchState(time.current).amount
  })
  return <lineSegments geometry={geometry} material={material} frustumCulled={false}/>

}

export function SavantContourLight({ time, active, color = "#e5ad39" }: {
  time: React.MutableRefObject<number>; active: boolean; color?: string
}) {
  return <group>
    <ContourRunner time={time} active={active} color={color} side={1} />
    <ContourRunner time={time} active={active} color={color} side={-1} />
    <ContourCrossLinks time={time} active={active} color={color} />
  </group>
}
