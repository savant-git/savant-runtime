import {forwardRef,useId} from "react"
import type {SVGProps} from "react"
import {savantIconPaths} from "./savant-icon-paths"
import type {SavantIconName} from "./savant-icon-paths"
export type GlyphProps=Omit<SVGProps<SVGSVGElement>,"name">&{size?:number|string;title?:string;tone?:"single"|"duotone"}
type IconProps=GlyphProps&{name:SavantIconName}
/** Accessible inline SVG, no font dependency, remote requests or per-icon effects. */
export const SavantIcon=forwardRef<SVGSVGElement,IconProps>(function SavantIcon(
 {name,size=20,title,tone="duotone",className="",strokeWidth=1.8,children,...props},ref){
 const titleId=useId()
 const labelled=Boolean(title||props["aria-label"]||props["aria-labelledby"])
 const [main,detail]=savantIconPaths[name]
 return <svg xmlns="http://www.w3.org/2000/svg" ref={ref}
  width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
  strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round"
  className={["savant-glyph",className].filter(Boolean).join(" ")}
  focusable="false" role={labelled?"img":undefined}
  aria-hidden={labelled?undefined:true} aria-labelledby={title?titleId:undefined} {...props}>
  {title&&<title id={titleId}>{title}</title>}
  <path d={main}/>
  {detail&&<path d={detail} opacity={tone==="duotone"?.72:1}/>}
  {children}
 </svg>
})
function createGlyph(name:SavantIconName){
 const Icon=forwardRef<SVGSVGElement,GlyphProps>((props,ref)=><SavantIcon name={name} ref={ref} {...props}/>)
 Icon.displayName="savant-"+name
 return Icon
}
export const BookOpen=createGlyph("book-open")
export const BrainCircuit=createGlyph("brain-circuit")
export const Braces=createGlyph("braces")
export const ClipboardList=createGlyph("clipboard-list")
export const Columns2=createGlyph("columns2")
export const Focus=createGlyph("focus")
export const Gauge=createGlyph("gauge")
export const Link2=createGlyph("link2")
export const MessageSquareText=createGlyph("message-square-text")
export const PanelLeft=createGlyph("panel-left")
export const PanelRight=createGlyph("panel-right")
export const RotateCcw=createGlyph("rotate-ccw")
export const Search=createGlyph("search")
export const Server=createGlyph("server")
export const SquareTerminal=createGlyph("square-terminal")
export const Command=createGlyph("command")
export const Rows3=createGlyph("rows3")
export const HelpCircle=createGlyph("help-circle")
export const MaterialPrism=createGlyph("material-prism")
export const ParticleHelix=createGlyph("particle-helix")
export const ReflectionField=createGlyph("reflection-field")
export const ElectricalArc=createGlyph("electrical-arc")
export const TopologyMesh=createGlyph("topology-mesh")
export const ReplayTimeline=createGlyph("replay-timeline")
export const Activity=createGlyph("activity")
export const ArrowLeft=createGlyph("arrow-left")
export const ArrowRight=createGlyph("arrow-right")
export const Bot=createGlyph("bot")
export const Check=createGlyph("check")
export const ChevronDown=createGlyph("chevron-down")
export const Clock3=createGlyph("clock3")
export const GitBranch=createGlyph("git-branch")
export const Layers3=createGlyph("layers3")
export const Orbit=createGlyph("orbit")
export const Pause=createGlyph("pause")
export const Play=createGlyph("play")
export const ScanEye=createGlyph("scan-eye")
export const Sparkles=createGlyph("sparkles")
export const X=createGlyph("x")
export const Clipboard=createGlyph("clipboard")
export const Code2=createGlyph("code2")
export const CornerDownLeft=createGlyph("corner-down-left")
export const Download=createGlyph("download")
export const FilePlus2=createGlyph("file-plus2")
export const FileText=createGlyph("file-text")
export const Image=createGlyph("image")
export const LoaderCircle=createGlyph("loader-circle")
export const Pencil=createGlyph("pencil")
export const Plus=createGlyph("plus")
export const RefreshCw=createGlyph("refresh-cw")
export const Send=createGlyph("send")
export const Square=createGlyph("square")
export const Trash2=createGlyph("trash2")
export const UserRound=createGlyph("user-round")
export const VolumeX=createGlyph("volume-x")
export const Blocks=createGlyph("blocks")
export const Camera=createGlyph("camera")
export const FileSearch=createGlyph("file-search")
export const Globe2=createGlyph("globe2")
export const Library=createGlyph("library")
export const Mic=createGlyph("mic")
export const Paperclip=createGlyph("paperclip")
export const WandSparkles=createGlyph("wand-sparkles")
export const CircleDot=createGlyph("circle-dot")
export const Database=createGlyph("database")
export const ShieldCheck=createGlyph("shield-check")
export const ChevronRight=createGlyph("chevron-right")
export const File=createGlyph("file")
export const Maximize2=createGlyph("maximize2")
export const Minimize2=createGlyph("minimize2")
export {SquareTerminal as TerminalSquare,HelpCircle as CircleHelp}
