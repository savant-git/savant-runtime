import {Box3,BufferGeometry,Group,Mesh,MeshDepthMaterial,MeshPhysicalMaterial,Object3D,RGBADepthPacking,Vector3} from "three"
import {installSurface} from "./savant-surfaces"
import type {EffectUniforms} from "./savant-surfaces"
import {cleanLogoGeometry} from "./savant-geometry"
export function prepareModel(source:Object3D,uniforms:EffectUniforms){
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
