import React,{useLayoutEffect} from "react"
import {useThree} from "@react-three/fiber"
import {BackSide,Color,Mesh,MeshPhysicalMaterial,PMREMGenerator,Scene,ShaderMaterial,SphereGeometry} from "three"
const palette={
 uSavantReflectionPink:{value:new Color("#ff2f9d")},
 uSavantReflectionGold:{value:new Color("#d6b45f")},
}
/* Smooth angular radiance sources, convolved analytically by roughness.
 * These are directional studio emitters, not ray-traced object reflections. */
export const reflectionGLSL=`
uniform vec3 uSavantReflectionPink,uSavantReflectionGold;
float savantSoftSheet(vec3 d,vec3 axis,float stretch,float width,float bend,float roughness){
 vec3 n=normalize(axis);
 vec3 tangent=normalize(cross(abs(n.y)<.9?vec3(0,1,0):vec3(1,0,0),n));
 vec3 up=cross(n,tangent);
 float x=dot(d,tangent),y=dot(d,up);
 float curve=y+bend*sin(x*4.0);
 float w=max(width+roughness*roughness*.38,fwidth(curve)*1.3);
 float l=stretch+roughness*roughness*.35;
 return exp(-.5*(x*x/(l*l)+curve*curve/(w*w)))*smoothstep(.1,.65,dot(d,n));
}
vec3 savantReflectionRadiance(vec3 d,float roughness,float time){
 vec3 value=vec3(.035,.042,.05);
 for(int i=0;i<5;i++){
  float id=float(i);
  float speed=.8+id*.19;
  float a=time*speed+id*1.91+.21*sin(time*.73+id);
  vec3 axis=normalize(vec3(cos(a),sin(a*.67+id)*.68,sin(a)));
  float stretch=.29+id*.045,width=.045+id*.009;
  float soft=savantSoftSheet(d,axis,stretch,width,.055*sin(time*.91+id),roughness);
  vec3 tint=i==0||i==3?uSavantReflectionPink:i==1||i==4?uSavantReflectionGold:vec3(.65,.76,.83);
  value+=tint*soft*(1.4+.2*cos(time*1.13+id));
 }
 float ceiling=exp(-pow((d.y-.7)/(.28+roughness*.2),2.0));
 return value+vec3(.22,.27,.31)*ceiling;
}
`
export function installDynamicReflections(material:MeshPhysicalMaterial,time:{value:number}){
 const previous=material.onBeforeCompile,key=material.customProgramCacheKey.bind(material)
 material.onBeforeCompile=(shader,renderer)=>{
  previous.call(material,shader,renderer)
  Object.assign(shader.uniforms,palette,{uSavantReflectionTime:time})
  shader.fragmentShader=shader.fragmentShader.replace("#include <common>",
   "#include <common>\nuniform float uSavantReflectionTime;\n"+reflectionGLSL)
   .replace("#include <lights_fragment_maps>",`#include <lights_fragment_maps>
    #if defined(RE_IndirectSpecular)
     vec3 savantRay=reflect(-geometryViewDir,geometryNormal);
     savantRay=normalize(mix(savantRay,geometryNormal,material.roughness*material.roughness));
     vec3 savantWorldRay=inverseTransformDirection(savantRay,viewMatrix);
     radiance+=savantReflectionRadiance(savantWorldRay,material.roughness,uSavantReflectionTime);
     #ifdef USE_CLEARCOAT
      vec3 savantCoatRay=inverseTransformDirection(reflect(-geometryViewDir,geometryClearcoatNormal),viewMatrix);
      clearcoatRadiance+=savantReflectionRadiance(savantCoatRay,material.clearcoatRoughness,uSavantReflectionTime)*.65;
     #endif
    #endif
   `)
 }
 material.customProgramCacheKey=()=>key()+":savant-smooth-radiance-1"
}
/* Generate a filtered studio foundation once. The moving sources above update
 * directly in the main material; there is no per-frame cubemap/PMREM capture. */
export function SavantReflectionEnvironment(){
 const {gl,scene,invalidate}=useThree()
 useLayoutEffect(()=>{
  const stage=new Scene(),geometry=new SphereGeometry(12,24,12)
  const material=new ShaderMaterial({
   side:BackSide,toneMapped:false,uniforms:palette,
   vertexShader:`varying vec3 vDirection;void main(){vDirection=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
   fragmentShader:`varying vec3 vDirection;`+reflectionGLSL+`
    void main(){gl_FragColor=vec4(savantReflectionRadiance(normalize(vDirection),.24,0.0)*.22,1.0);}
   `,
  })
  stage.add(new Mesh(geometry,material))
  const generator=new PMREMGenerator(gl)
  const previous=scene.environment
  let target:ReturnType<PMREMGenerator["fromScene"]>|null=null
  try{
   target=generator.fromScene(stage,.06,.1,30,{size:256})
   scene.environment=target.texture;invalidate()
  }catch(error){
   // Dynamic physical reflections still work without the optional foundation.
   console.warn("savant studio foundation unavailable",error)
  }finally{geometry.dispose();material.dispose()}
  return()=>{
   if(target&&scene.environment===target.texture)scene.environment=previous
   target?.dispose();generator.dispose()
  }
 },[gl,scene,invalidate])
 return null
}
