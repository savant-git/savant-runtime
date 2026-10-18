import {BoxGeometry,Group,InstancedMesh,MeshStandardMaterial,MeshBasicMaterial,Object3D,Color,DirectionalLight,HemisphereLight} from "three"
/** Reflection-only miniature: instanced hull plates, buttresses, conduits and running lights. */
export function derelictStage(){
 const group=new Group(),box=new BoxGeometry(1,1,1),dummy=new Object3D()
 const hullMaterial=new MeshStandardMaterial({color:"#46545a",metalness:.78,roughness:.34})
 const lampsMaterial=new MeshBasicMaterial({color:new Color(3.2,1.7,.55),toneMapped:false})
 const hull=new InstancedMesh(box,hullMaterial,360),lamps=new InstancedMesh(box,lampsMaterial,48)
 let index=0
 function part(x:number,y:number,z:number,sx:number,sy:number,sz:number){
  dummy.position.set(x,y,z);dummy.rotation.set(0,0,0);dummy.scale.set(sx,sy,sz);dummy.updateMatrix()
  hull.setMatrixAt(index++,dummy.matrix)
 }
 part(0,0,0,7,.6,1.3)
 for(let i=0;i<28;i++){
  const x=(i-13.5)*.245,step=(i%5)*.025
  part(x,.35+step,0,.19,.08+step,1.45)
  part(x,-.36,0,.035,.25,1.55)
  for(const side of [-1,1]){
   part(x,.05,side*.76,.15,.33,.055)
   part(x,-.05,side*.81,.045,.5,.06)
  }
 }
 for(let i=0;i<18;i++)part((i-8.5)*.35,.49,Math.sin(i*1.7)*.48,.045,.12,.7)
 for(let i=0;i<8;i++){
  const x=(i-3.5)*.76
  part(x,.7,0,.22,.6,.48);part(x,.95,.1,.4,.08,.6)
 }
 for(let i=0;i<42;i++)part((i%21-10)*.3,-.08+(i%3)*.11,i<21?-.84:.84,.2,.05,.025)
 hull.count=index;hull.instanceMatrix.needsUpdate=true
 for(let i=0;i<48;i++){
  dummy.position.set((i%24-11.5)*.27,.12,i<24?-.85:.85)
  dummy.scale.set(.035,.022,.025);dummy.updateMatrix();lamps.setMatrixAt(i,dummy.matrix)
 }
 lamps.instanceMatrix.needsUpdate=true
 const key=new DirectionalLight("#d8f2ff",4);key.position.set(-3,4,3)
 const fill=new HemisphereLight("#adc7cd","#141c25",1.1)
 group.add(hull,lamps,key,fill);group.position.set(0,.8,-6);group.rotation.y=.15
 return {group,dispose(){box.dispose();hullMaterial.dispose();lampsMaterial.dispose();group.clear()}}
}
