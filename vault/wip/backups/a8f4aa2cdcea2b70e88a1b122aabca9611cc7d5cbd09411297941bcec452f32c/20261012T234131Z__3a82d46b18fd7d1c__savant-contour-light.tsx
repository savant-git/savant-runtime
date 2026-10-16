import React, { useEffect, useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { AdditiveBlending, CatmullRomCurve3, Color, DoubleSide, Mesh, ShaderMaterial, TubeGeometry, Vector3, BufferGeometry, Float32BufferAttribute, MeshPhysicalMaterial, IcosahedronGeometry, PointLight } from "three"
import { glitchState } from "./savant-motion"
import { savantContour, savantContourFrontZ } from "./savant-contour-data"

const turnsPerSecond = 0.095
const wakeSeconds = 10.25
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
        float loose=sin(vUv.x*17.0-uTime*11.0)+.55*sin(vUv.x*31.0+uTime*7.0);
        p.x+=uGlitch*.12*loose*sin(vUv.x*11.0+uTime*9.0);
        p.y+=uGlitch*.10*loose*cos(vUv.x*9.0-uTime*8.0);
        p.z+=uGlitch*.07*sin(vUv.x*23.0+uTime*12.0);
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
        gl_FragColor=vec4(tint*3.0,clamp(alpha,0.,.94));
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

/** One seamless geometric braid row is revealed every 0.2 seconds.
 * Each row consists of joined, repeating three-way angular motifs, not carbon weave.
 * Vertex progression produces a DrawSVG-style reveal in WebGL without a DOM SVG overlay.
 */
function ContourCrossLinks({ time, active, color }: {
  time: React.MutableRefObject<number>; active: boolean; color: string
}) {
  const interval = .2
  const count = Math.round(1 / (turnsPerSecond * interval))
  const front = Math.abs(savantContourFrontZ) + .018
  const curve = useMemo(() => new CatmullRomCurve3(
    savantContour.map(([x,y]) => new Vector3(x,y,0)), true, "centripetal", .5
  ), [])
  const geometry = useMemo(() => {
    const vertices: number[] = []
    const phases: number[] = []
    const progress: number[] = []
    const strand: number[] = []
    const emit = (a: Vector3,b: Vector3,phase: number,pa: number,pb: number,seed: number) => {
      vertices.push(a.x,a.y,a.z,b.x,b.y,b.z)
      phases.push(phase,phase)
      progress.push(pa,pb)
      strand.push(seed,seed)
    }
    // Repeating interlocked chevron/Y glyphs across the depth of the S.
    // One row is one contiguous stroke with small secondary branching strokes.
    const steps=12
    for(let i=0;i<count;i++){
      const phase=i/count
      const center=curve.getPointAt(phase)
      const tangent=curve.getTangentAt(phase).normalize()
      const normal=new Vector3(-tangent.y,tangent.x,0)
      const point=(j:number,offset:number)=>{
        const depth=j/steps
        const zig=(j%4===0?0:j%4===1?1:j%4===2?0:-1)
        return center.clone().addScaledVector(normal,(zig*.052+offset)).add(new Vector3(0,0,-front+2*front*depth))
      }
      // Continuous main zigzag across the thickness.
      for(let j=0;j<steps;j++)emit(point(j,0),point(j+1,0),phase,j/(steps+4),(j+1)/(steps+4),i)
      // Paired arms create the repeating interlocked hexagonal / three-pronged pattern.
      for(let j=0;j<steps;j+=4){
        const start=point(j+1,0)
        const tipA=point(j+2,.070)
        const tipB=point(j+2,-.070)
        emit(start,tipA,phase,(steps+j/2)/(steps+4),(steps+j/2+.5)/(steps+4),i)
        emit(start,tipB,phase,(steps+j/2+.5)/(steps+4),(steps+j/2+1)/(steps+4),i)
      }
    }
    const g=new BufferGeometry()
    g.setAttribute("position",new Float32BufferAttribute(vertices,3))
    g.setAttribute("aPhase",new Float32BufferAttribute(phases,1))
    g.setAttribute("aProgress",new Float32BufferAttribute(progress,1))
    g.setAttribute("aSeed",new Float32BufferAttribute(strand,1))
    return g
  },[curve,count,front])
  const material=useMemo(()=>new ShaderMaterial({
    transparent:true,depthWrite:false,depthTest:true,blending:AdditiveBlending,toneMapped:false,
    uniforms:{uTime:{value:0},uActive:{value:0},uColor:{value:new Color(color)},uGlitch:{value:0}},
    vertexShader:`attribute float aPhase,aProgress,aSeed;
      varying float vPhase,vProgress;uniform float uTime,uGlitch;
      void main(){vPhase=aPhase;vProgress=aProgress;vec3 p=position;
        float wave=sin(aProgress*15.0-uTime*10.0+aSeed*.31)+.45*sin(aProgress*27.0+uTime*8.0+aSeed*.19);
        float curl=sin(aProgress*9.0+uTime*7.0+aSeed*.13);
        p.x+=uGlitch*.12*wave*curl;
        p.y+=uGlitch*.13*wave*sin(aProgress*12.0-uTime*6.0);
        p.z+=uGlitch*.055*cos(aProgress*19.0+uTime*9.0+aSeed*.3);
        gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);}`,
    fragmentShader:`varying float vPhase,vProgress;uniform float uTime,uActive;uniform vec3 uColor;
      void main(){
        float head=fract(uTime*${turnsPerSecond.toFixed(6)});
        float age=fract(head-vPhase+1.)/${turnsPerSecond.toFixed(6)};
        float reveal=smoothstep(vProgress-.035,vProgress+.035,clamp(age/${interval.toFixed(2)},0.,1.));
        float fade=1.-smoothstep(.25,${wakeSeconds.toFixed(2)},age);
        float throb=1.05+.23*pow(.5+.5*sin(uTime*1.83),3.);
        float alpha=uActive*reveal*fade*throb;
        if(alpha<.008)discard;
        vec3 tint=mix(uColor,vec3(1.,.10,.47),smoothstep(4.8,${wakeSeconds.toFixed(2)},age));
        gl_FragColor=vec4(tint*2.9,clamp(alpha,0.,.93));}`,
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
