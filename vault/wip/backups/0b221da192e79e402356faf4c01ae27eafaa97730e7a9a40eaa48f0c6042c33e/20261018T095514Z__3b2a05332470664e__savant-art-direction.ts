import type {MaterialPreset} from "./savant-surfaces"
export type ArtShape="sphere"|"shard"|"crystal"|"ring"|"leaf"|"tile"|"ribbon"
export type ArtDirection={
 kind:number;name:string;summary:string;paper:string;ink:string;accent:string;secondary:string
 shape:ArtShape;size:number;stretch:number;speed:number;spin:number;energy:number
 haze:number;drift:number;softness:number;emission:number;edge:number
}
type Row=[string,string,string,string,string,ArtShape,number,number,number,number,number,number,number,number,number,number,string]
const rows:readonly Row[]=[
 ["illustration glaze","#e5caaa","#352c28","#b86d45","#7899a7","tile",.8,1.1,.74,.6,.85,.07,.08,.12,.2,.18,"Warm layered illustration, canvas-like strokes, cream highlights and quiet floating paper flecks."],
 ["dark heroic oil","#bf8d53","#1b1520","#f08d3c","#6c4a62","shard",1.15,1.7,.88,1.1,1.1,.18,.14,.17,.65,.36,"Deep bronze oil-brush shading, dense warm smoke, ember shards and dramatic grazing light."],
 ["desert ink cel","#eee4b8","#263d46","#76c7c8","#df8760","ribbon",.9,2.3,.76,.5,.65,.06,.07,.14,.1,.85,"Pastel cel planes, precise contour ink, fine drawn bands and light ribbon particles."],
 ["biomechanical ribs","#96a49c","#121c1d","#a0c7b0","#8893a3","shard",1.1,2.4,.72,.8,.8,.15,.11,.09,.35,.5,"Tubular rib fields, cold organic-metal shading, narrow splinters and layered dark vapor."],
 ["polished fantasy airbrush","#dcb4a1","#302744","#f9d47f","#c083b8","crystal",1.15,1.4,.92,1.2,1.15,.12,.16,.08,.75,.22,"Glossy airbrush gradients, luminous mineral highlights, jewel particles and warm iridescent atmosphere."],
 ["woodland watercolor","#b9c7a2","#30483b","#c8d9b4","#9aacbf","leaf",1.15,1.8,.6,.55,.55,.22,.06,.2,.12,.42,"Soft watercolor pooling, muted forest pigments, drifting leaves and diffuse mist."],
 ["high contrast ink","#d8e1e1","#090c14","#8d9ab4","#d8c6b2","ribbon",.9,3,.84,.7,.6,.09,.12,.1,.15,1,"Extreme ink contrast, sparse pale edges, needle-like particles and smoky negative space."],
 ["faerie earth pigment","#a3ac72","#4a3a34","#d5c389","#b98bba","leaf",1.3,1.3,.57,.8,.65,.19,.09,.18,.25,.35,"Organic mottled pigment, soft earthen shading, seed-like leaves and pollen haze."],
 ["kinetic cyber facets","#819ce9","#101a37","#ffcc53","#fb678e","shard",1.2,2.6,1.18,2,1.2,.1,.3,.07,1.1,.7,"Angular color facets, electric accents, fast shard silhouettes and a restrained fractured aura."],
 ["monolithic cinema","#bea57d","#1c2830","#edb16d","#88a6b6","tile",1.1,1.8,.61,.4,.85,.24,.055,.18,.18,.12,"Broad mineral planes, amber/cool cinematic separation, heavy quiet motes and long diffused haze."],
 ["wet nocturne","#a9adb5","#111924","#c24c42","#b6c8cf","sphere",.85,1.9,.92,1,1.05,.17,.18,.07,.55,.3,"Wet noir streaks, deep shadows, warm practical glints and drifting rain-like particles."],
 ["crimson celluloid","#f1cf62","#171519","#ce3341","#f2d96e","tile",1.05,1.2,1.08,1.4,.95,.08,.23,.1,.3,.9,"Sharp crimson/yellow blocks, film-print scratches, hard editorial lighting and graphic tile flecks."],
 ["recursive engraving","#e3e1d4","#2c2b3c","#bab6d4","#9293a5","tile",1,1.1,.72,.65,.65,.065,.08,.13,.08,.85,"Recursive isometric cells, crosshatching, monochrome illumination and interlocking tile particles."],
 ["chromatic poster","#f6d17d","#222538","#f45270","#48a7c4","ribbon",1.25,3.2,.9,1,.85,.09,.17,.14,.35,.85,"Flat poster pigments, curved chromatic bands, flowing ribbons and a broad graphic halo."],
 ["action enamel","#e3d6b9","#23252b","#d44b62","#3695ae","sphere",1.05,1.5,1.2,2.2,1,.13,.29,.11,.4,.3,"Layered splash/drip marks, thrown paint-like flecks, energetic trails and spattered atmosphere."],
 ["corroded ink reliquary","#b8a06c","#30241f","#aa493b","#bdab7b","shard",1.1,2.2,.8,1.2,.8,.2,.12,.16,.25,.75,"Rusty stippled ink, dense fine hatch, worn gold edges and smoky needle fragments."],
 ["alchemical symmetry","#dfbf7e","#392543","#ba72dd","#e9bc52","ring",1.25,1,.78,1.3,1.05,.14,.2,.13,.75,.6,"Mirrored alchemical bands, jewel-like rays, rotating rings and a symmetric luminous atmosphere."],
 ["tactile creature felt","#b9a9bb","#483944","#b88ecd","#94cbbd","sphere",1.35,1.2,.56,.5,.55,.12,.07,.22,.12,.25,"Soft felt-like fiber shading, rounded tactile motes, gentle pastel trails and diffuse light."],
 ["industrial hull cinema","#adb9c1","#1a2930","#c5e4eb","#daa969","shard",1.1,2.5,.88,1.1,1,.19,.16,.1,.5,.4,"Panel seams and brushed hull bands, cool specular strips, hot fragments and damp industrial haze."],
 ["stencil aerosol","#e3e5dc","#1a252a","#dd6b4b","#a8b7ad","tile",1.05,1.5,.82,.8,.7,.1,.1,.18,.08,1,"High-contrast stencil blocks, stippled spray edges, flat graphic flakes and a soft aerosol veil."],
]
export const artDirections:readonly ArtDirection[]=rows.map((r,kind)=>({
 kind,name:r[0],paper:r[1],ink:r[2],accent:r[3],secondary:r[4],shape:r[5],
 size:r[6],stretch:r[7],speed:r[8],spin:r[9],energy:r[10],haze:r[11],
 drift:r[12],softness:r[13],emission:r[14],edge:r[15],summary:r[16],
}))
export const neutralArt:ArtDirection={
 kind:-1,name:"cinematic PBR",summary:"Current black-chrome/copper PBR treatment with gold-to-pink trails and hot sparks.",
 paper:"#d6b45f",ink:"#17242a",accent:"#ff5422",secondary:"#ff2f9d",
 shape:"sphere",size:1,stretch:1.5,speed:1,spin:1,energy:1,haze:0,drift:.34,
 softness:.09,emission:1,edge:0,
}
export function artDirectionFor(preset:MaterialPreset):ArtDirection{
 return preset.id==="black-chrome"||preset.id==="palaver-copper-titanium"?
  neutralArt:artDirections[preset.style]||neutralArt
}
