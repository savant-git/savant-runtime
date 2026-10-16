import React, { useEffect, useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { AdditiveBlending, CatmullRomCurve3, Color, Mesh, ShaderMaterial, TubeGeometry, Vector3 } from "three"
import { savantContour, savantContourFrontZ } from "./savant-contour-data"

/** The trajectory is derived from the supplied GLB silhouette, not a generic S. */
export function SavantContourLight({ time, active, color = "#d6b45f" }: {
  time: React.MutableRefObject<number>
  active: boolean
  color?: string
}) {
  const head = useRef<Mesh>(null)
  const curve = useMemo(() => new CatmullRomCurve3(
    savantContour.map(([x, y]) => new Vector3(x, y, savantContourFrontZ)), true, "centripetal", 0.5
  ), [])
  const geometry = useMemo(() => new TubeGeometry(curve, 384, 0.006, 5, true), [curve])
  const material = useMemo(() => new ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
    uniforms: {
      uTime: { value: 0 },
      uActive: { value: 1 },
      uColor: { value: new Color(color) },
    },
    vertexShader: `varying vec2 vUv; void main() { vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `
      varying vec2 vUv;
      uniform float uTime;
      uniform float uActive;
      uniform vec3 uColor;
      void main() {
        float head=fract(uTime*0.095);
        float behind=fract(head-vUv.x+1.0);
        float wake=pow(1.0-smoothstep(0.0,0.42,behind),1.6);
        float fadeIn=smoothstep(0.0,0.016,behind);
        float glimmer=0.85+0.15*sin(vUv.x*140.0-uTime*5.0);
        float alpha=uActive*wake*fadeIn*glimmer*0.88;
        if(alpha<0.008) discard;
        gl_FragColor=vec4(mix(uColor,vec3(0.88,0.95,1.0),0.28),alpha);
      }`,
  }), [])
  useEffect(() => { material.uniforms.uColor.value.set(color) }, [material, color])
  useEffect(() => () => { geometry.dispose(); material.dispose() }, [geometry, material])
  useFrame(() => {
    material.uniforms.uTime.value = time.current
    material.uniforms.uActive.value = active ? 1 : 0
    if (head.current) {
      const t = ((time.current * 0.095) % 1 + 1) % 1
      head.current.position.copy(curve.getPointAt(t))
      const s = active ? 1 + 0.17 * Math.sin(time.current * 9) : 0.85
      head.current.scale.setScalar(s)
    }
  })
  return <group>
    <mesh geometry={geometry} material={material} frustumCulled={false} />
    <mesh ref={head}>
      <sphereGeometry args={[0.022, 12, 8]} />
      <meshBasicMaterial color={color} toneMapped={false} />
    </mesh>
  </group>
}
