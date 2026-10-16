import React, { useEffect, useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { AdditiveBlending, CatmullRomCurve3, Color, DoubleSide, Mesh, ShaderMaterial, TubeGeometry, Vector3, BufferGeometry, Float32BufferAttribute } from "three"
import { savantContour, savantContourFrontZ } from "./savant-contour-data"

const turnsPerSecond = 0.095
const wakeSeconds = 7.5
const orbit = (time: number) => ((time * turnsPerSecond) % 1 + 1) % 1

function ContourRunner({ time, active, color, direction, side }: {
  time: React.MutableRefObject<number>; active: boolean; color: string; side: 1 | -1
}) {
  const head = useRef<Mesh>(null)
  const curve = useMemo(() => new CatmullRomCurve3(
    savantContour.map(([x, y]) => new Vector3(x, y, side * (Math.abs(savantContourFrontZ) + .018))),
    true, "centripetal", .5,
  ), [side])
  const geometry = useMemo(() => new TubeGeometry(curve, 512, .018, 7, true), [curve])
  const material = useMemo(() => new ShaderMaterial({
    transparent: true, depthWrite: false, depthTest: true, side: DoubleSide,
    blending: AdditiveBlending, toneMapped: false,
    uniforms: {
      uTime: { value: 0 }, uActive: { value: 0 }, uColor: { value: new Color(color) },
      uDirection: { value: 1 }, uPhase: { value: 0 },
      uDuration: { value: wakeSeconds },
    },
    vertexShader: `varying vec2 vUv; varying vec3 vWorld;
      void main(){vUv=uv;vWorld=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
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
        float alpha=uActive*fade*widening*diffusion*(1.35+bloom*1.4);
        if(alpha<.006)discard;
        vec3 tint=mix(uColor,vec3(.72,.91,1.),.26+afterOne*.18);
        gl_FragColor=vec4(tint*2.6,clamp(alpha,0.,1.));
      }`,
  }), [])
  useEffect(() => { material.uniforms.uColor.value.set(color) }, [material, color])
  useEffect(() => () => { geometry.dispose(); material.dispose() }, [geometry, material])
  useFrame(() => {
    material.uniforms.uTime.value = time.current
    material.uniforms.uActive.value = active ? 1 : 0
    if (head.current) {
      head.current.position.copy(curve.getPointAt(orbit(time.current)))
      head.current.scale.setScalar(active ? 1 + .12 * Math.sin(time.current * 8) : .75)
      head.current.visible = active
    }
  })
  return <group>
    <mesh geometry={geometry} material={material} frustumCulled={false} />
    <mesh ref={head}>
      <sphereGeometry args={[.052, 20, 16]} />
      <meshBasicMaterial color={color} toneMapped={false} />
    </mesh>
  </group>
}

/** One source contour drives both faces and the synchronized cross-thickness links. */
function ContourCrossLinks({ time, active, color }: {
  time: React.MutableRefObject<number>; active: boolean; color: string
}) {
  const count = Math.max(1, Math.round(1 / (turnsPerSecond * .5)))
  const front = Math.abs(savantContourFrontZ) + .018
  const curve = useMemo(() => new CatmullRomCurve3(
    savantContour.map(([x,y]) => new Vector3(x,y,0)), true, "centripetal", .5
  ), [])
  const geometry = useMemo(() => {
    const points: number[] = []
    const indices: number[] = []
    for (let i=0;i<count;i++) {
      const p = curve.getPointAt(i/count)
      points.push(p.x,p.y,-front,p.x,p.y,front)
      indices.push(i,i)
    }
    const g = new BufferGeometry()
    g.setAttribute("position", new Float32BufferAttribute(points,3))
    g.setAttribute("aIndex",new Float32BufferAttribute(indices,1))
    return g
  }, [curve,count,front])
  const material = useMemo(() => new ShaderMaterial({
    transparent:true, depthWrite:false, depthTest:true, blending:AdditiveBlending,
    uniforms:{uTime:{value:0},uActive:{value:0},uColor:{value:new Color(color)}},
    vertexShader:`attribute float aIndex; varying float vIndex; void main(){vIndex=aIndex;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`uniform float uTime,uActive;uniform vec3 uColor;varying float vIndex;
      void main(){float phase=vIndex/${count.toFixed(1)};float head=fract(uTime*${turnsPerSecond.toFixed(6)});
      float age=fract(head-phase+1.)/${turnsPerSecond.toFixed(6)};
      float appear=smoothstep(.0,.12,age);float fade=1.-smoothstep(.12,${wakeSeconds.toFixed(1)},age);
      float alpha=uActive*appear*fade*.95;if(alpha<.005)discard;gl_FragColor=vec4(uColor*2.5,clamp(alpha,0.,1.));}`,
  }),[color])
  useEffect(()=>()=>{geometry.dispose();material.dispose()},[geometry,material])
  useFrame(()=>{material.uniforms.uTime.value=time.current;material.uniforms.uActive.value=active?1:0})
  return <lineSegments geometry={geometry} material={material} frustumCulled={false}/>
}

export function SavantContourLight({ time, active, color = "#d6b45f" }: {
  time: React.MutableRefObject<number>; active: boolean; color?: string
}) {
  return <group>
    <ContourRunner time={time} active={active} color={color} side={1} />
    <ContourRunner time={time} active={active} color={color} side={-1} />
    <ContourCrossLinks time={time} active={active} color={color} />
  </group>
}
