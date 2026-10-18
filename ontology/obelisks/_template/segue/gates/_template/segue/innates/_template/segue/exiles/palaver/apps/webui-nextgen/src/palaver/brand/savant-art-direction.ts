import type {MaterialPreset} from "./savant-surfaces"
export type ArtShape="sphere"|"shard"|"crystal"|"ring"|"leaf"|"tile"|"ribbon"
export type ArtDirection={
 kind:number;name:string;summary:string;paper:string;ink:string;accent:string;secondary:string
 shape:ArtShape;size:number;stretch:number;speed:number;spin:number;energy:number
 haze:number;drift:number;softness:number;emission:number;edge:number
 metal:number;rough:number;coat:number;sheen:number;relief:number;graphic:number
}

type Definition=[string,string,string,string,string,ArtShape,number,number,number,number,string]
const definitions:readonly Definition[]=[
 [
  "bastion · emerald titanium",
  "#428d78",
  "#111c25",
  "#e7bd68",
  "#dc526a",
  "crystal",
  0.88,
  0.24,
  0.82,
  0.12,
  "Stepped titanium terraces, armored lens cells and warm reactor seams."
 ],
 [
  "citadel · obsidian gold",
  "#43474b",
  "#101519",
  "#dfb762",
  "#b87b94",
  "shard",
  0.96,
  0.21,
  1,
  0.1,
  "Dark polished armor, nested hexagonal lenses and gold microarchitecture."
 ],
 [
  "vesper · porcelain exosuit",
  "#dadbd1",
  "#293b47",
  "#da686a",
  "#92bbc5",
  "tile",
  0.32,
  0.23,
  0.95,
  0.11,
  "Ivory ceramic lamellae, inset isometric ribs and restrained crimson separators."
 ],
 [
  "scarab · petrol iridium",
  "#407c86",
  "#182333",
  "#bca7db",
  "#d8bf7f",
  "crystal",
  0.91,
  0.19,
  1,
  0.1,
  "Iridescent beetle-armor facets, diagonally interlocked chambers and mineral highlights."
 ],
 [
  "reliquary · oxblood alloy",
  "#8c414e",
  "#221a28",
  "#e0bb7c",
  "#9caeb5",
  "shard",
  0.79,
  0.28,
  0.88,
  0.14,
  "Crimson plated terraces, engraved crest forms and cold metal edges."
 ],
 [
  "sentinel · arctic cobalt",
  "#567fba",
  "#172536",
  "#d6e7eb",
  "#dda96b",
  "tile",
  0.85,
  0.25,
  0.9,
  0.12,
  "Interlocking blue architectural armor with bright inset lens arrays."
 ],
 [
  "cathedral · smoked platinum",
  "#9daab1",
  "#27303c",
  "#b9a3ce",
  "#d5bb85",
  "ribbon",
  0.95,
  0.22,
  0.92,
  0.14,
  "Tall buttressed plate fields, platinum ribs and violet optical insets."
 ],
 [
  "cinder · volcanic bronze",
  "#a16c48",
  "#261e24",
  "#efb673",
  "#bda4bb",
  "shard",
  0.9,
  0.29,
  0.8,
  0.15,
  "Bronze heat-shield tessellation, vented isometric courses and amber seams."
 ],
 [
  "chrysalis · jade enamel",
  "#62a797",
  "#18383a",
  "#d8c99a",
  "#da8a9b",
  "leaf",
  0.56,
  0.24,
  1,
  0.12,
  "Nested jade shell panels, organic lens clusters and ivory terrace edges."
 ],
 [
  "sovereign · amethyst steel",
  "#7f6b9b",
  "#242137",
  "#dec091",
  "#8dc3c5",
  "crystal",
  0.87,
  0.2,
  0.95,
  0.13,
  "Gem-cut armored chambers, fine stepped recesses and cool inset facets."
 ]
]
export const artDirections:readonly ArtDirection[]=definitions.map((r,kind)=>({
 kind,name:r[0],paper:r[1],ink:r[2],accent:r[3],secondary:r[4],shape:r[5],
 metal:r[6],rough:r[7],coat:r[8],relief:r[9],summary:r[10],
 sheen:0,emission:.08,graphic:0,edge:.12,size:1.12,stretch:1.35+(kind%3)*.3,
 speed:.88+(kind%4)*.055,spin:.7+(kind%3)*.25,energy:1.12,
 haze:.045,drift:.15+(kind%3)*.025,softness:.065
}))
export const neutralArt:ArtDirection=artDirections[0]
export function artDirectionFor(preset:MaterialPreset):ArtDirection{
 return artDirections[Math.max(0,Math.min(9,Math.trunc(preset.style)))]||artDirections[0]
}
