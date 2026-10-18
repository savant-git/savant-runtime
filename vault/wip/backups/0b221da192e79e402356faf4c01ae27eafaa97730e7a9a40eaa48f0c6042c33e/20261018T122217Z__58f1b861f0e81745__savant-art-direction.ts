import type {MaterialPreset} from "./savant-surfaces"
export type ArtShape="sphere"|"shard"|"crystal"|"ring"|"leaf"|"tile"|"ribbon"
export type ArtDirection={
 kind:number;name:string;summary:string;paper:string;ink:string;accent:string;secondary:string
 shape:ArtShape;size:number;stretch:number;speed:number;spin:number;energy:number
 haze:number;drift:number;softness:number;emission:number;edge:number
 metal:number;rough:number;coat:number;sheen:number;relief:number;graphic:number
}
type Definition=[string,string,string,string,string,ArtShape,number,number,number,number,number,number,number,number,number,string]
const definitions:readonly Definition[]=[
 ["ridley scott · derelict reflection","#67757f","#111920","#e6b961","#8abec7","shard",.94,.19,1,0,0,0,.018,1.4,1,"Smooth untextured alloy reflecting an animated procedural derelict hull, ribs, conduits and intermittent running lamps."],
 ["xenomorph · wet carapace","#2d3834","#070c10","#a4cc8a","#8c9eaa","shard",.84,.22,.95,0,.018,0,.09,2.8,.78,"Wet chitin ribs, nested scales, acidic specular seams, needle fragments and cold vapor."],
 ["puuung · lamplit miniature","#eac69f","#514c66","#f7bd72","#b4cbbd","leaf",.02,.69,.25,.3,.01,.7,.018,1.5,.58,"Soft storybook pigment, warm window-shaped illumination, drifting leaves and gentle lamplit haze."],
 ["moebius · desert engraving","#efe5b7","#314851","#80c9cf","#ed9879","ribbon",.04,.62,.2,0,0,1,.016,2.7,.72,"Pastel stepped planes, fine cross-contours, desert strata and airborne drawn ribbons."],
 ["salvador dali · liquid clockwork","#d9a155","#302c48","#efc878","#81becb","ring",.65,.17,.95,0,.006,0,.045,1,.75,"Flowing elongated contours, liquid metallic optical waves, clock-like orbiting rings and desert mirage."],
 ["kamen rider · armored metamorph","#3c896d","#12242a","#dc454e","#c9dbaf","crystal",.83,.23,1,0,0,.2,.07,1.6,1.2,"Segmented insect armor, lens-like cells, contrasting red seams and rapid crystalline motes."],
 ["ancient heraldry · repoussé","#bd9b53","#3c2524","#a52f49","#d1c7a1","tile",.9,.35,.6,0,0,.15,.08,1.2,.65,"Embossed lozenges, engraved chevrons, aged gilding and scarlet ceremonial flecks."],
 ["bioluminescence · abyssal tissue","#133b40","#06151c","#61f7c7","#657bff","sphere",.12,.28,.85,.45,.11,0,.04,1.2,.65,"Traveling luminous capillaries, translucent-looking optical layers and pulsing plankton."],
 ["nick park · sculpted clay","#cda483","#4c3732","#b66a53","#bac496","sphere",0,.82,.1,.12,0,0,.055,1.3,.55,"Rounded clay shading, broad thumbprint relief, soft earthy motes and miniature-stage light."],
 ["furry · silver guard hair","#b6b0a4","#363642","#d9c39b","#939cc1","leaf",.02,.88,.1,.95,0,0,.10,3,.7,"Analytical directional fiber lobes, soft guard-hair glints and elongated floating tufts."],
 ["pixar · polished character resin","#58afbd","#193347","#f4bd6d","#e48b99","sphere",.05,.22,1,.35,.012,0,.012,1.2,.82,"Rounded layered resin, soft warm/cool key separation and buoyant polished motes."],
 ["albert dubout · crowded ink","#e7cfa1","#342d2e","#c96949","#8e9776","tile",.01,.76,.12,0,0,1,.025,1.1,.88,"Dense curling caricature marks, warm wash, overlapping ink shapes and restless paper fragments."],
 ["claudia rogge · repeated tableaux","#c7c4bc","#282b31","#ab8988","#7e8d9c","sphere",.16,.47,.6,.1,0,.25,.04,1.9,.74,"Dense repeated sculptural motifs, precise studio falloff and ordered drifting miniature forms."],
 ["tomer hanuka · graphic nocturne","#9aabc4","#302742","#e56372","#d4ae72","ribbon",.04,.57,.25,0,.012,1,.02,2.6,.87,"Crisp limited-color planes, winding negative shapes and sharp editorial ribbons."],
 ["the dark crystal · mineral puppetry","#a7a28b","#322f43","#bd91da","#a9cab0","crystal",.38,.34,.8,.5,.02,0,.065,1.5,.62,"Opalescent mineral veins, layered organic ridges, crystal splinters and woodland spores."],
 ["grimdark · ossuary iron","#675a53","#16131e","#a23853","#c6a375","shard",.77,.46,.55,0,.018,.2,.095,3,.9,"Serrated relic engraving, bruised iron, ember fissures and sparse ashen shards."],
 ["isometric · microarchitecture","#c4d9d8","#284149","#e0b775","#8295c4","tile",.44,.32,.7,0,0,.8,.085,1.2,.72,"Three-axis architectural cells, inset terraces, tiny window fields and cuboid motes."],
 ["julie paschkis · botanical geometry","#ebcc82","#3e4244","#bb534e","#5f9a89","leaf",.02,.71,.18,.12,0,1,.02,1.7,.62,"Interwoven leaf and petal constructions, rich folk pigments and floating botanical silhouettes."],
 ["rick baker · creature workshop","#b3a18c","#332e32","#b66e67","#94a58d","sphere",.03,.48,.55,.65,.006,0,.075,1.7,.75,"Layered creature-skin folds, pore-scale shading, wet highlights and organic resin beads."],
 ["steve cutts · satirical ink","#c4b9a0","#252b2d","#be5c47","#829289","tile",.02,.79,.08,0,0,1,.035,1.4,.91,"Dense drawn hatching, mechanical repetition, limited dusty pigment and tumbling graphic scraps."]
]
export const artDirections:readonly ArtDirection[]=definitions.map((r,kind)=>({
 kind,name:r[0],paper:r[1],ink:r[2],accent:r[3],secondary:r[4],shape:r[5],
 metal:r[6],rough:r[7],coat:r[8],sheen:r[9],emission:r[10],graphic:r[11],relief:r[12],
 stretch:r[13],speed:r[14],summary:r[15],size:kind===9?1.35:1.1,
 spin:kind===5?1.8:kind===12?.55:1,energy:kind===15?1.05:1.15,
 haze:kind===0?.10:kind===7?.17:.08,drift:kind===0?.04:.12+(kind%4)*.035,
 softness:kind===0?.035:kind===9?.16:.085,edge:r[11]*.8
}))
export const neutralArt:ArtDirection={
 kind:-1,name:"cinematic PBR",summary:"Black chrome or copper/titanium cinematic treatment.",
 paper:"#d6b45f",ink:"#17242a",accent:"#ff5422",secondary:"#ff2f9d",
 shape:"sphere",size:1,stretch:1.5,speed:1,spin:1,energy:1,haze:0,drift:.34,
 softness:.09,emission:1,edge:0,metal:1,rough:.19,coat:1,sheen:0,relief:0,graphic:0
}
export function artDirectionFor(preset:MaterialPreset):ArtDirection{
 return preset.id==="black-chrome"||preset.id==="palaver-copper-titanium"?
  neutralArt:artDirections[preset.style]||neutralArt
}
