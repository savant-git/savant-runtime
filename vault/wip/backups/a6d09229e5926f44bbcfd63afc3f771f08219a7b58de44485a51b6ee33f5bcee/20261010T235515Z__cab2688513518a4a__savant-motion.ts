/* Shared bounded motion primitives. Visual randomness is reproducible. */
export const motion = {
  headerParticles: 18,
  preloaderParticles: 26,
  trailSamples: 96,
  trailSeconds: 4.2,
  radius: .81,
  radiusSpread: .025,
  height: 2.5,
  rise: .09,
  riseSpread: .035,
  glitchPeriod: 36,
  glitchMin: 1,
  glitchMax: 2,
}

export function seeded(value: number) {
  const n = Math.sin(value * 127.1 + 311.7) * 43758.5453123
  return n - Math.floor(n)
}

export function ease(value: number) {
  const t = Math.max(0, Math.min(1, value))
  return t * t * t * (t * (t * 6 - 15) + 10)
}

export function glitchState(time: number) {
  const epoch = Math.floor(time / motion.glitchPeriod)
  const local = time - epoch * motion.glitchPeriod
  const start = 8 + seeded(epoch + 1) * 10
  const duration = motion.glitchMin +
    seeded(epoch + 91) * (motion.glitchMax - motion.glitchMin)
  const age = local - start

  if (age <= 0 || age >= duration) {
    return { amount: 0, duration, age }
  }

  const envelope = ease(age / .085) *
    (1 - ease((age - duration + .18) / .18))

  const pulse = .38 +
    .22 * Math.abs(Math.sin(age * 23)) +
    .19 * Math.abs(Math.sin(age * 47.3 + epoch)) +
    .21 * Math.abs(Math.sin(age * 91.7 + epoch * 1.7))

  const dropout =
    seeded(epoch * 71 + Math.floor(age * 32)) > .86 ? .22 : 1

  return {
    amount: Math.min(1, envelope * pulse * 1.75 * dropout),
    duration,
    age,
  }
}

export function damp(
  current: number,
  target: number,
  rate: number,
  delta: number,
) {
  return current + (target - current) *
    (1 - Math.exp(-rate * Math.max(0, Math.min(delta, .1))))
}

export function flowClock(id: number, time: number) {
  const phase = seeded(id + 401) * Math.PI * 2
  return time +
    .18 * (Math.sin(time * .73 + phase) - Math.sin(phase)) / .73 +
    .12 * (Math.sin(time * 1.31 + phase * 1.7) -
      Math.sin(phase * 1.7)) / 1.31
}

const glslFloat = (value: number) => value.toFixed(8)

export const trajectoryGLSL = [
  "uniform float uEmitterCount,uTime,uYaw,uPitch,uMoving,uEffect,uRatio,uHeadScale,uStretch,uViewport;",
  "uniform vec3 uColor,uAccent;",
  "float phash(float n){return fract(sin(n*127.1+311.7)*43758.5453123);}",
  "float ease5(float t){t=clamp(t,0.0,1.0);return t*t*t*(t*(t*6.0-15.0)+10.0);}",
  "float riseSpeed(float id){return " + glslFloat(motion.rise) + "+phash(id+20.0)*" + glslFloat(motion.riseSpread) + ";}",
  "float flowClock(float id,float time){",
  " float phase=phash(id+401.0)*6.2831853;",
  " return time+.18*(sin(time*.73+phase)-sin(phase))/.73+",
  "  .12*(sin(time*1.31+phase*1.7)-sin(phase*1.7))/1.31;",
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
  " float clock=flowClock(id,time),travel=fract(travelAt(id,time));",
  " float phase=uYaw+travel*6.2831853*2.3;",
  " float radius=" + glslFloat(motion.radius) + "+phash(id+13.0)*" + glslFloat(motion.radiusSpread) + "+.015*sin(clock*2.1+id);",
  " vec3 p=vec3(cos(phase)*radius,(travel-.5)*" + glslFloat(motion.height) + ",sin(phase)*radius);",
  " float winding=time*6.8+lag*19.0+id*2.1;",
  " float coil=.065*ease5(lag/" + glslFloat(motion.trailSeconds) + ");",
  " float secondary=sin(winding*1.7+id)*.008*ease5(lag);",
  " p+=vec3(cos(phase)*cos(winding),sin(winding),sin(phase)*cos(winding))*(coil+secondary);",
  " return axisRotate(p);",
  "}",
  "float gleam(float id){",
  " float period=3.0+phash(id+101.0)*5.0;",
  " float age=mod(uTime+phash(id+100.0)*5.0,period);",
  " return uMoving*ease5(age/.025)*(1.0-ease5((age-.025)/.15));",
  "}",
  "mat3 particleSpin(float id){",
  " float angle=flowClock(id,uTime)*(.5+phash(id+87.0)*.8)+id;",
  " float c=cos(angle),s=sin(angle);",
  " return mat3(c,0.0,-s,0.0,1.0,0.0,s,0.0,c);",
  "}"
].join("\n");
