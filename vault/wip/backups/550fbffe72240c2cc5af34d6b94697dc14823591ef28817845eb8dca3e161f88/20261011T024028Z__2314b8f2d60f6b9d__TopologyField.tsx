import { Canvas,useFrame } from "@react-three/fiber"
import { useRef } from "react"
import * as THREE from "three"

function Topology(){

  const ref =
    useRef<THREE.LineSegments>(null)

  useFrame((state)=>{

    if(!ref.current) return

    ref.current.rotation.y =
      state.clock.elapsedTime * 0.02

    ref.current.rotation.x =
      state.clock.elapsedTime * 0.01
  })

  return (
    <lineSegments ref={ref}>
      <edgesGeometry
        args={[
          new THREE.IcosahedronGeometry(
            2.5,
            4
          )
        ]}
      />
      <lineBasicMaterial
        transparent
        opacity={0.08}
      />
    </lineSegments>
  )
}

export default function TopologyField(){

  return (
    <Canvas camera={{
      position:[0,0,6]
    }}>
      <Topology />
    </Canvas>
  )
}
