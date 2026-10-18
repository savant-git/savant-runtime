import {Box3,BufferGeometry,Group,Mesh,MeshPhysicalMaterial,Object3D,Vector3} from "three"
import {installArtSurface} from "./savant-art-surface"
import type {ArtUniforms} from "./savant-art-surface"
import {installTitleGlitch} from "./savant-title-motion"
import type {TitleGlitch} from "./savant-title-motion"
/** Own only cloned GPU resources. Preserve the GLB's hard-edge normals and topology. */
export function prepareStudioModel(source:Object3D,glitch:TitleGlitch,art:ArtUniforms){
 const model=new Group(),clone=source.clone(true),geometries:BufferGeometry[]=[]
 const material=new MeshPhysicalMaterial({
  name:"savant-instrument-model-v2",color:"#515963",
  metalness:1,roughness:.19,clearcoat:1,clearcoatRoughness:.13,
  envMapIntensity:1.35,dithering:true,flatShading:false,
 })
 clone.traverse(object=>{
  if(!(object instanceof Mesh))return
  const geometry=object.geometry.clone(),position=geometry.getAttribute("position")
  if(!position)throw new Error("savant logo has no position attribute")
  if(!geometry.getAttribute("normal"))geometry.computeVertexNormals()
  geometry.deleteAttribute("color")
  geometry.computeBoundingBox();geometry.computeBoundingSphere()
  object.geometry=geometry;object.material=material
  object.customDepthMaterial=undefined;object.castShadow=false;object.receiveShadow=false
  geometries.push(geometry)
 })
 model.add(clone);model.updateMatrixWorld(true)
 const bounds=new Box3().setFromObject(model)
 if(bounds.isEmpty())throw new Error("savant logo has empty bounds")
 const extent=bounds.getSize(new Vector3()),center=bounds.getCenter(new Vector3())
 const scale=2/Math.max(extent.x,extent.y,extent.z,.0001)
 installTitleGlitch(material,glitch,scale,center.y,1.6)
 installArtSurface(material,art,scale,center.y)
 model.name="savant-instrument-model-v2"
 model.scale.setScalar(scale);model.position.copy(center).multiplyScalar(-scale)
 model.scale.z*=1.6;model.position.z*=1.6;model.updateMatrixWorld(true)
 return {model,material,geometries,bounds:new Box3().setFromObject(model)}
}
