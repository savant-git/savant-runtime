/* Analytical, derivative-filtered surface fields: no downloaded texture maps,
 * no quantized noise, no UV seams. PBR lighting still owns the final shading. */
export const fieldDeclarations=`
uniform float uSavantTime,uSavantStyle,uEvent,uEventProgress;
uniform vec3 uSavantAccent,uAccent2;
varying vec3 vFieldPoint;
float ridge(float value,float width){
 float aa=max(fwidth(value)*1.25,.001);
 return 1.0-smoothstep(width-aa,width+aa,abs(value));
}
float cells(vec2 p){
 vec2 f=fract(p)-.5;
 return min(abs(f.x),abs(f.y));
}
vec4 surfaceField(vec3 p){
 float t=uSavantTime,s=uSavantStyle;
 float f=0.0,r=0.0,e=0.0,coat=1.0;
 if(s<.5){f=.5+.5*sin(p.y*19.0+t*.8+sin(p.x*9.0));r=.045*f;}
 else if(s<1.5){f=ridge(cells(p.xy*9.0),.014);e=f*.25;r=f*.03;}
 else if(s<2.5){f=.5+.5*sin(p.x*95.0+sin(p.y*18.0)*.3);r=.055*f;}
 else if(s<3.5){f=.5+.5*sin(dot(p,vec3(23.0,9.0,18.0))+t*.5);r=f*.02;}
 else if(s<4.5){f=.5+.5*sin(p.y*47.0+sin(p.x*21.0)*3.0);r=f*.12;}
 else if(s<5.5){f=ridge(sin(p.y*100.0-t*5.0),.12);e=f*(.1+uEvent*.6);r=.02*f;}
 else if(s<6.5){f=.5+.5*sin(p.y*8.0+p.x*5.0+t+sin(p.z*12.0));e=f*.08;r=.025*f;}
 else if(s<7.5){f=ridge(sin(p.x*17.0+p.y*21.0+sin(p.z*13.0)),.055);r=f*.18*uEvent;e=f*uEvent*.07;}
 else if(s<8.5){f=.5+.5*sin(p.x*13.0+p.y*7.0+t*1.3+sin(p.z*19.0+t));r=.009*f;}
 else if(s<9.5){f=.5+.5*sin(length(p.xy)*26.0-t*2.0+sin(p.z*11.0));r=f*.025;e=f*.035;}
 else if(s<10.5){
  vec2 q=p.xy*11.0;vec2 id=floor(q);vec2 local=fract(q)-.5;
  float hash=fract(sin(dot(id,vec2(17.1,53.7)))*43758.5);
  float radius=.07+hash*.27;
  f=(1.0-smoothstep(radius-.015,radius+.015,length(local+vec2(sin(hash*9.0),cos(hash*17.0))*.12)))*uEvent;
  r=f*.18;coat=1.0-f*.4;
 }else if(s<11.5){f=.5+.5*sin(p.y*11.0+p.x*4.0+t+sin(p.z*7.0+t*.4));r=f*.015;}
 else if(s<12.5){f=ridge(cells(p.xy*7.0),.023);e=f*(.15+.45*uEvent);r=f*.12;}
 else if(s<13.5){f=.5+.5*sin(p.y*37.0+sin(p.x*13.0+t)*3.0);e=f*.06;r=f*.055;}
 else if(s<14.5){f=ridge(sin(p.y*41.0+p.x*6.0-t*3.0),.09);e=f*.13;r=f*.025;}
 else if(s<15.5){f=ridge(cells(p.xy*17.0+vec2(0.0,t*.1)),.017);e=f*.18;r=f*.08;}
 else if(s<16.5){f=.5+.5*sin(dot(p,vec3(19.0,27.0,7.0))+t*.4);r=f*.02;}
 else if(s<17.5){f=.5+.5*sin(p.y*19.0+t*3.0+sin(p.x*15.0+t)*2.0);e=f*.25;r=f*.035;}
 else if(s<18.5){f=.5+.5*sin(p.x*53.0+sin(p.y*37.0)*2.0);r=f*.17;}
 else if(s<19.5){f=ridge(sin(length(p.xy)*33.0-t),.035);e=f*.08;r=f*.035;}
 else{
  // Alloy transition: low-frequency corrosion basins and anisotropic machined ridges.
  // All terms are analytical and derivative-filtered to avoid UV seams.
  vec3 q=p*vec3(3.7,4.2,3.9);
  float basin=.5+.5*sin(q.x*2.4+sin(q.z*1.9)*1.7+sin(q.y*1.6));
  float erosion=.5+.5*sin(dot(q,vec3(1.7,2.9,.8))+sin(q.x*3.2)*.65);
  float patina=smoothstep(.48,.73,basin*.67+erosion*.33);
  float cut=ridge(sin(p.y*117.0+p.x*13.0+sin(p.z*21.0)*.24),.09);
  float grain=.5+.5*sin(p.y*251.0+p.z*31.0);
  f=clamp(patina*.72+cut*.19+grain*.09,0.0,1.0);
  r=patina*.14+cut*.026;
  e=cut*uEvent*.12;
  coat=1.0-patina*.38;
 }
 return vec4(clamp(f,0.0,1.0),r,e,coat);
}`;
