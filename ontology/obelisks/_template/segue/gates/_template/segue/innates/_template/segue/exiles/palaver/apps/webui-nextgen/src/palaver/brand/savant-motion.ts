/* Shared bounded motion primitives. Visual randomness is reproducible. */
export const motion = {
 headerParticles:14,preloaderParticles:22,trailSamples:72,trailSeconds:1.0,
 radius:.72,radiusSpread:.09,height:2.65,rise:.21,riseSpread:.075,
 glitchPeriod:6.7,glitchMin:.40,glitchMax:1.05,
}
export function seeded(value:number){
 const n=Math.sin(value*127.1+311.7)*43758.5453123
 return n-Math.floor(n)
}
export function ease(value:number){
 const t=Math.max(0,Math.min(1,value));return t*t*t*(t*(t*6-15)+10)
}
export function glitchState(time:number){
 const epoch=Math.floor(time/motion.glitchPeriod)
 const local=time-epoch*motion.glitchPeriod
 const start=.7+seeded(epoch+1)*1.5
 const duration=motion.glitchMin+seeded(epoch+91)*(motion.glitchMax-motion.glitchMin)
 const age=local-start
 if(age<=0||age>=duration)return {amount:0,duration,age}
 const envelope=ease(age/.085)*(1-ease((age-duration+.18)/.18))
 const pulse=.38+.22*Math.abs(Math.sin(age*23))+
  .19*Math.abs(Math.sin(age*47.3+epoch))+
  .21*Math.abs(Math.sin(age*91.7+epoch*1.7))
 const dropout=seeded(epoch*71+Math.floor(age*32))>.86?.22:1
 return {amount:Math.min(1,envelope*pulse*2.65*dropout),duration,age}
}
export function damp(current:number,target:number,rate:number,delta:number){
 return current+(target-current)*(1-Math.exp(-rate*Math.max(0,Math.min(delta,.1))))
}
export function flowClock(id:number,time:number){
 const phase=seeded(id+401)*Math.PI*2
 return time+.18*(Math.sin(time*.73+phase)-Math.sin(phase))/.73+
  .12*(Math.sin(time*1.31+phase*1.7)-Math.sin(phase*1.7))/1.31
}
const glslFloat=(value:number)=>value.toFixed(8)
export const trajectoryGLSL = [
  "uniform float uEmitterCount,uTime,uYaw,uPitch,uMoving,uEffect,uRatio,uHeadScale,uStretch,uViewport;",
  "uniform vec3 uColor,uAccent;",
  "float phash(float n){return fract(sin(n*127.1+311.7)*43758.5453123);}",
  "float ease5(float t){t=clamp(t,0.0,1.0);return t*t*t*(t*(t*6.0-15.0)+10.0);}",
  "float riseSpeed(float id){return " + glslFloat(motion.rise) + "+phash(id+20.0)*" + glslFloat(motion.riseSpread) + ";}",
  "float cubicBezier(float t,float p1,float p2){float a=1.0-t;return 3.0*a*a*t*p1+3.0*a*t*t*p2+t*t*t;}",
  "float easeCurve(float t,float kind){t=clamp(t,0.0,1.0);if(kind<1.0)return t*t*(3.0-2.0*t);if(kind<2.0)return ease5(t);if(kind<3.0)return .5-.5*cos(3.14159265*t);return cubicBezier(t,.12,.88);}",
  "float flowClock(float id,float time){",
  " float phase=phash(id+401.0)*6.2831853;",
  " float interval=2.4+phash(id+502.0)*2.6;",
  " float epoch=floor(time/interval),fraction=fract(time/interval);",
  " float previous=phash(id*19.0+epoch-1.0),next=phash(id*19.0+epoch);",
  " float curve=easeCurve(fraction,floor(phash(id+epoch*13.0)*4.0));",
  " float variation=mix(previous,next,curve);",
  " return time+.18*(sin(time*.73+phase)-sin(phase))/.73+",
  "  .12*(sin(time*1.31+phase*1.7)-sin(phase*1.7))/1.31+",
  "  .18*sin(time*.57+phase)*(.35+.65*variation);",
  "}",
  "float travelAt(float id,float time){return flowClock(id,time)*riseSpeed(id)+phash(id+5.0);}",
  "vec3 life(float id){",
  " if(uMoving<.5||uTime<2.0)return vec3(9.0,1.0,0.0);",
  " float clock=uTime-2.0,event=floor(clock/4.8),age=mod(clock,4.8);",
  " float chosen=floor(phash(event+903.0)*uEmitterCount);",
  " if(abs(id-chosen)>.5)return vec3(age,1.0,0.0);",
  " return vec3(age,ease5((age-3.0)/.75),1.0);",
  "}",
  "vec3 axisRotate(vec3 p){",
  " float c=cos(uPitch),s=sin(uPitch);",
  " return vec3(p.x,p.y*c-p.z*s,p.y*s+p.z*c);",
  "}",
  "vec3 helix(float id,float time,float lag){",
  " float pair=floor(id*.5),side=mod(id,2.0)<.5?1.0:-1.0;",
  " float pairs=max(1.0,ceil(uEmitterCount*.5));",
  " float phase=6.2831853*(time*0.095+pair/pairs);",
  " float rise=fract(time*0.095+pair/pairs);",
  " float major=phase*3.0;",
  " float minor=major*3.0;",
  " float radius=" + glslFloat(motion.radius) + ";",
  " float detail=0.065*sin(minor);",
  " float x=cos(major)*(radius+detail);",
  " float z=sin(major)*(radius+detail);",
  " float y=(rise-.5)*" + glslFloat(motion.height) + "+0.035*cos(minor);",
  " return axisRotate(vec3(side*x,y,side*z));",
  "}",
  "float gleam(float id){",
  " float period=3.0+phash(id+101.0)*5.0;",
  " float age=mod(uTime+phash(id+100.0)*5.0,period);",
  " return uMoving*ease5(age/.025)*(1.0-ease5((age-.025)/.15));",
  "}",
  "mat3 particleSpin(float id){",
  " float angle=flowClock(id,uTime)*(1.9+phash(id+87.0)*8.4)+id;",
  " vec3 axis=normalize(vec3(phash(id+17.0)*2.0-1.0,phash(id+31.0)*2.0-1.0,phash(id+53.0)*2.0-1.0)+vec3(.001));",
  " float c=cos(angle),s=sin(angle),v=1.0-c;",
  " float x=axis.x,y=axis.y,z=axis.z;",
  " return mat3(c+x*x*v,y*x*v+z*s,z*x*v-y*s, x*y*v-z*s,c+y*y*v,z*y*v+x*s, x*z*v+y*s,y*z*v-x*s,c+z*z*v);",
  "}"
].join("\n");

/* Safe analytical clock for consumers resuming after suspended rendering. */
export function stableSceneTime(time:number){
 return Number.isFinite(time)?Math.max(0,time):0
}
