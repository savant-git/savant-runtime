import {useLayoutEffect} from "react"
import {useThree} from "@react-three/fiber"
import {DataTexture,DataUtils,EquirectangularReflectionMapping,HalfFloatType,LinearFilter,LinearSRGBColorSpace,PMREMGenerator,RGBAFormat} from "three"

/** One immutable HDR studio, filtered once; no scene lamps or recurring captures. */
export function SavantStudio(){
 const {gl,scene,invalidate}=useThree()
 useLayoutEffect(()=>{
  const width=1024,height=512
  const pixels=new Uint16Array(width*height*4)
  const lobes=[
   {x:.48,y:.55,z:.68,width:.32,height:.72,r:1.6,g:1.65,b:1.7},
   {x:-.83,y:.25,z:-.49,width:.48,height:.65,r:.85,g:.92,b:1.0},
   {x:-.3,y:.2,z:.93,width:.6,height:.4,r:.23,g:.08,b:.15},
   {x:.56,y:-.14,z:-.82,width:.5,height:.55,r:.3,g:.22,b:.1},
  ].map(source=>{
   const n=Math.hypot(source.x,source.y,source.z)
   const x=source.x/n,y=source.y/n,z=source.z/n
   const t=Math.hypot(x,z)
   return {...source,x,y,z,tx:z/t,tz:-x/t,ux:-y*x/t,uy:t,uz:-y*z/t}
  })
  const half=DataUtils.toHalfFloat
  for(let row=0;row<height;row++){
   const latitude=Math.PI*(row+.5)/height
   const dy=-Math.cos(latitude),radial=Math.sin(latitude)
   for(let col=0;col<width;col++){
    const longitude=2*Math.PI*(col+.5)/width-Math.PI
    const dx=radial*Math.cos(longitude),dz=radial*Math.sin(longitude)
    const ceiling=.3*Math.pow(Math.max(dy,0),.8)
    let r=.19+ceiling,g=.22+ceiling,b=.24+ceiling
    for(const source of lobes){
     const facing=dx*source.x+dy*source.y+dz*source.z
     if(facing<=0)continue
     const u=(dx*source.tx+dz*source.tz)/source.width
     const v=(dx*source.ux+dy*source.uy+dz*source.uz)/source.height
     const gate=Math.min(1,facing/.35)
     const value=Math.exp(-.5*(u*u+v*v))*gate*gate*(3-2*gate)
     r+=source.r*value;g+=source.g*value;b+=source.b*value
    }
    const at=(row*width+col)*4
    pixels[at]=half(r);pixels[at+1]=half(g);pixels[at+2]=half(b);pixels[at+3]=half(1)
   }
  }
  const source=new DataTexture(pixels,width,height,RGBAFormat,HalfFloatType)
  source.colorSpace=LinearSRGBColorSpace
  source.mapping=EquirectangularReflectionMapping
  source.minFilter=LinearFilter;source.magFilter=LinearFilter
  source.generateMipmaps=false;source.needsUpdate=true
  const generator=new PMREMGenerator(gl)
  const previous=scene.environment,previousIntensity=scene.environmentIntensity
  const previousRotation=scene.environmentRotation.clone()
  let target:ReturnType<PMREMGenerator["fromEquirectangular"]>|null=null
  try{
   target=generator.fromEquirectangular(source)
   scene.environment=target.texture;scene.environmentIntensity=1
   invalidate()
  }finally{
   source.dispose();generator.dispose()
  }
  return()=>{
   if(target&&scene.environment===target.texture){
    scene.environment=previous;scene.environmentIntensity=previousIntensity
    scene.environmentRotation.copy(previousRotation)
   }
   target?.dispose()
  }
 },[gl,scene,invalidate])
 return null
}
