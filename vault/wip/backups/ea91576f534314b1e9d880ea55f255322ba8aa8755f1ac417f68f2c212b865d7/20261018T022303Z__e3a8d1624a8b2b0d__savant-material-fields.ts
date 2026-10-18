/* Twenty material-specific analytical patterns. Geometry, depth and PBR shading share style IDs. */
export const fieldDeclarations = `
uniform float uSavantTime,uSavantStyle,uEvent,uEventProgress;
uniform vec3 uSavantAccent,uAccent2;
varying vec3 vFieldPoint;
float savantHash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
float savantRidge(float x,float w){return 1.0-smoothstep(w-fwidth(x),w+fwidth(x),abs(x));}
vec4 surfaceField(vec3 p){
 float t=uSavantTime; float s=uSavantStyle; vec3 q=p;
 float pigment=0.0,relief=0.0,emission=0.0,coat=1.0;
 // Smooth hybrid patina; no cell/floor noise or high-frequency normal steps.
 if(s>19.5){
  float phase=q.x*12.0+q.y*8.0+sin(q.z*7.0)*1.4;
  float attenuation=exp(-fwidth(phase)*fwidth(phase));
  float oxide=.5+.18*sin(phase)*attenuation;
  return vec4(oxide,.012*oxide,0.0,1.0);
 }
 if(s<0.5){
  float pattern=sin(q.x*11.0+sin(q.y*7.0))*sin(q.z*12.0);
  float grain=savantHash(floor(q*16.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.035;
  emission=pow(max(0.0,pattern),2.0)*0.050*(.7+.3*uEvent);
  coat=clamp(0.50+.2*pattern,0.1,1.0);
 }
 else if(s<1.5){
  float pattern=sin(length(q.xz)*38.0+q.y*17.0+sin(q.z*11.0));
  float grain=savantHash(floor(q*23.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.049;
  emission=pow(max(0.0,pattern),3.0)*0.105*(.7+.3*uEvent);
  coat=clamp(0.62+.2*pattern,0.1,1.0);
 }
 else if(s<2.5){
  float pattern=savantRidge(sin(q.x*22.0+q.y*8.0),.14);
  float grain=savantHash(floor(q*30.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.063;
  emission=pow(max(0.0,pattern),4.0)*0.160*(.7+.3*uEvent);
  coat=clamp(0.74+.2*pattern,0.1,1.0);
 }
 else if(s<3.5){
  float pattern=sin(q.y*67.0+sin(q.x*16.0)*2.5);
  float grain=savantHash(floor(q*37.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.077;
  emission=pow(max(0.0,pattern),5.0)*0.215*(.7+.3*uEvent);
  coat=clamp(0.86+.2*pattern,0.1,1.0);
 }
 else if(s<4.5){
  float pattern=sin(atan(q.y,q.x)*17.0+length(q.xy)*13.0);
  float grain=savantHash(floor(q*44.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.091;
  emission=pow(max(0.0,pattern),2.0)*0.050*(.7+.3*uEvent);
  coat=clamp(0.50+.2*pattern,0.1,1.0);
 }
 else if(s<5.5){
  float pattern=sin(q.x*9.0+sin(q.y*18.0+q.z*8.0));
  float grain=savantHash(floor(q*51.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.035;
  emission=pow(max(0.0,pattern),3.0)*0.105*(.7+.3*uEvent);
  coat=clamp(0.62+.2*pattern,0.1,1.0);
 }
 else if(s<6.5){
  float pattern=savantRidge(sin(q.y*28.0+q.z*11.0),.12);
  float grain=savantHash(floor(q*16.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.049;
  emission=pow(max(0.0,pattern),4.0)*0.160*(.7+.3*uEvent);
  coat=clamp(0.74+.2*pattern,0.1,1.0);
 }
 else if(s<7.5){
  float pattern=sin(length(q.xy)*26.0+sin(q.z*17.0));
  float grain=savantHash(floor(q*23.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.063;
  emission=pow(max(0.0,pattern),5.0)*0.215*(.7+.3*uEvent);
  coat=clamp(0.86+.2*pattern,0.1,1.0);
 }
 else if(s<8.5){
  float pattern=sin(q.x*41.0+sin(q.y*13.0)*4.0);
  float grain=savantHash(floor(q*30.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.077;
  emission=pow(max(0.0,pattern),2.0)*0.050*(.7+.3*uEvent);
  coat=clamp(0.50+.2*pattern,0.1,1.0);
 }
 else if(s<9.5){
  float pattern=sin(q.y*103.0+q.z*13.0);
  float grain=savantHash(floor(q*37.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.091;
  emission=pow(max(0.0,pattern),3.0)*0.105*(.7+.3*uEvent);
  coat=clamp(0.62+.2*pattern,0.1,1.0);
 }
 else if(s<10.5){
  float pattern=sin(q.x*23.0+q.y*11.0+t*.17);
  float grain=savantHash(floor(q*44.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.035;
  emission=pow(max(0.0,pattern),4.0)*0.160*(.7+.3*uEvent);
  coat=clamp(0.74+.2*pattern,0.1,1.0);
 }
 else if(s<11.5){
  float pattern=savantRidge(sin(q.x*19.0+q.y*27.0),.18);
  float grain=savantHash(floor(q*51.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.049;
  emission=pow(max(0.0,pattern),5.0)*0.215*(.7+.3*uEvent);
  coat=clamp(0.86+.2*pattern,0.1,1.0);
 }
 else if(s<12.5){
  float pattern=sin(q.x*18.0)*sin(q.y*18.0)*sin(q.z*18.0);
  float grain=savantHash(floor(q*16.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.063;
  emission=pow(max(0.0,pattern),2.0)*0.050*(.7+.3*uEvent);
  coat=clamp(0.50+.2*pattern,0.1,1.0);
 }
 else if(s<13.5){
  float pattern=sin(atan(q.y,q.x)*9.0+length(q.xy)*34.0);
  float grain=savantHash(floor(q*23.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.077;
  emission=pow(max(0.0,pattern),3.0)*0.105*(.7+.3*uEvent);
  coat=clamp(0.62+.2*pattern,0.1,1.0);
 }
 else if(s<14.5){
  float pattern=sin(q.x*41.0+sin(q.y*71.0))*sin(q.z*37.0);
  float grain=savantHash(floor(q*30.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.091;
  emission=pow(max(0.0,pattern),4.0)*0.160*(.7+.3*uEvent);
  coat=clamp(0.74+.2*pattern,0.1,1.0);
 }
 else if(s<15.5){
  float pattern=sin(q.y*52.0+sin(q.x*31.0)*3.0);
  float grain=savantHash(floor(q*37.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.035;
  emission=pow(max(0.0,pattern),5.0)*0.215*(.7+.3*uEvent);
  coat=clamp(0.86+.2*pattern,0.1,1.0);
 }
 else if(s<16.5){
  float pattern=sin(length(q)*26.0+atan(q.y,q.x)*7.0);
  float grain=savantHash(floor(q*44.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.049;
  emission=pow(max(0.0,pattern),2.0)*0.050*(.7+.3*uEvent);
  coat=clamp(0.50+.2*pattern,0.1,1.0);
 }
 else if(s<17.5){
  float pattern=sin(q.x*15.0+q.y*19.0+sin(q.z*21.0));
  float grain=savantHash(floor(q*51.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.063;
  emission=pow(max(0.0,pattern),3.0)*0.105*(.7+.3*uEvent);
  coat=clamp(0.62+.2*pattern,0.1,1.0);
 }
 else if(s<18.5){
  float pattern=savantRidge(sin(q.y*87.0+q.x*9.0),.13);
  float grain=savantHash(floor(q*16.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.077;
  emission=pow(max(0.0,pattern),4.0)*0.160*(.7+.3*uEvent);
  coat=clamp(0.74+.2*pattern,0.1,1.0);
 }
 else if(s<19.5){
  float pattern=sin(q.x*13.0+sin(q.y*25.0)*3.0)*sin(q.z*15.0);
  float grain=savantHash(floor(q*23.0));
  pigment=clamp(.5+.32*pattern+.18*grain,0.0,1.0);
  relief=(pattern*.5+.5)*0.091;
  emission=pow(max(0.0,pattern),5.0)*0.215*(.7+.3*uEvent);
  coat=clamp(0.86+.2*pattern,0.1,1.0);
 }
 return vec4(pigment,relief,emission,coat);
}
`;
