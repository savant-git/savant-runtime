/** Camera-facing emissive/smoke sprites retain genuine 3D positions and depth occlusion. */
export const combustionVertex=`
attribute float aAge,aSeed;
varying vec2 vUv;varying float vAge,vSeed;
uniform float uTime;
void main(){
 vUv=uv;vAge=aAge;vSeed=aSeed;
 vec4 center=instanceMatrix*vec4(0.0,0.0,0.0,1.0);
 vec4 mv=modelViewMatrix*center;
 vec2 extent=vec2(length(instanceMatrix[0].xyz),length(instanceMatrix[1].xyz));
 float angle=.16*sin(aSeed*9.0+uTime*2.0);
 mat2 rotation=mat2(cos(angle),-sin(angle),sin(angle),cos(angle));
 mv.xy+=rotation*(position.xy*extent);
 gl_Position=projectionMatrix*mv;
}`
export const combustionNoise=`
float fireHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float fireNoise(vec2 p){
 vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
 return mix(mix(fireHash(i),fireHash(i+vec2(1,0)),f.x),mix(fireHash(i+vec2(0,1)),fireHash(i+vec2(1,1)),f.x),f.y);
}
float fireFbm(vec2 p){return fireNoise(p)*.57+fireNoise(p*2.03+7.1)*.29+fireNoise(p*4.11+13.7)*.14;}
`
export const flameFragment=`
uniform float uTime;uniform vec3 uGold,uPink;
varying vec2 vUv;varying float vAge,vSeed;
${combustionNoise}
void main(){
 vec2 p=vUv*2.0-1.0;
 float noise=fireFbm(vec2(p.x*2.7+vSeed*19.0,p.y*3.3-uTime*3.5));
 p.x+=sin(p.y*7.0-uTime*5.0+vSeed*21.0)*.12+(.5-noise)*.25;
 float width=mix(.52,.10,vUv.y);
 float core=exp(-p.x*p.x/max(width*width,.008));
 float vertical=smoothstep(-1.0,-.55,p.y)*(1.0-smoothstep(.35,1.0,p.y));
 float alpha=clamp(core*vertical*(.45+noise*.8)*pow(1.0-vAge,1.2),0.0,.85);
 vec3 tint=mix(uGold,uPink,smoothstep(.38,.68,vAge));
 vec3 heat=mix(tint,vec3(1.0,.91,.68),core*(1.0-vAge)*.7);
 gl_FragColor=vec4(heat*(1.1+core*1.5),alpha);
 #include <tonemapping_fragment>
 #include <colorspace_fragment>
}`
export const smokeFragment=`
uniform float uTime;uniform vec3 uSmoke,uLight;
varying vec2 vUv;varying float vAge,vSeed;
${combustionNoise}
void main(){
 vec2 p=vUv*2.0-1.0;
 float noise=fireFbm(p*2.2+vec2(vSeed*31.0,-uTime*.4));
 float radius=dot(p,p);
 float boundary=exp(-radius*3.7)*(1.0-smoothstep(.45,1.0,radius));
 float envelope=smoothstep(0.0,.2,vAge)*(1.0-smoothstep(.5,1.0,vAge));
 float alpha=boundary*envelope*(.45+noise*.55)*.19;
 vec3 lit=mix(uSmoke,uLight,clamp((1.0-vUv.x)*.3+noise*.14,0.0,.45));
 gl_FragColor=vec4(lit,alpha);
 #include <tonemapping_fragment>
 #include <colorspace_fragment>
}`
