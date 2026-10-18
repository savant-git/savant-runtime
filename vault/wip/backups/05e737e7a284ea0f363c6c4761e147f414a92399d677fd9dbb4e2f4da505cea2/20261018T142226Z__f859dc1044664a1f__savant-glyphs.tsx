import type { SVGProps } from "react"

type GlyphProps = SVGProps<SVGSVGElement> & { size?: number }

function Glyph({ size = 20, children, ...props }: GlyphProps) {
  return <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.55" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...props}>{children}</svg>
}

export function BookOpen(props: GlyphProps) { return <Glyph {...props}><path d="M12 5v15M12 7 7 4 3 5v14l4-1 5 2 5-2 4 1V5l-4-1-5 3Z"/><path d="M6 8h3m6 0h3"/></Glyph> }
export function BrainCircuit(props: GlyphProps) { return <Glyph {...props}><path d="M12 4 7 7v5l-3 3 4 5h8l4-5-3-3V7l-5-3Z"/><path d="M12 4v6m-5 2 5-2 5 2m-5-2v9M8 16h8"/></Glyph> }
export function Braces(props: GlyphProps) { return <Glyph {...props}><path d="M10 4H8L6 7v3l-3 2 3 2v3l2 3h2m4-16h2l2 3v3l3 2-3 2v3l-2 3h-2"/><path d="M11 16l2-8"/></Glyph> }
export function ClipboardList(props: GlyphProps) { return <Glyph {...props}><path d="M8 5H5v16h14V5h-3M9 3h6v4H9zM9 11h6m-6 4h6m-6 4h4"/></Glyph> }
export function Columns2(props: GlyphProps) { return <Glyph {...props}><path d="M3 4h18v16H3zM12 4v16M6 8h3m6 8h3"/></Glyph> }
export function Focus(props: GlyphProps) { return <Glyph {...props}><path d="M4 9V4h5m6 0h5v5m0 6v5h-5m-6 0H4v-5"/><circle cx="12" cy="12" r="3"/></Glyph> }
export function Gauge(props: GlyphProps) { return <Glyph {...props}><path d="M4 17a9 9 0 1 1 16 0M12 13l5-5M7 18h10"/><circle cx="12" cy="13" r="1"/></Glyph> }
export function Link2(props: GlyphProps) { return <Glyph {...props}><path d="M9 8 6 8 3 12l3 4h4m4-8h4l3 4-3 4h-4M8 12h8"/><circle cx="12" cy="12" r="1"/></Glyph> }
export function MessageSquareText(props: GlyphProps) { return <Glyph {...props}><path d="M3 4h18v13H9l-5 4v-4H3zM7 9h10M7 13h7"/></Glyph> }
export function PanelLeft(props: GlyphProps) { return <Glyph {...props}><path d="M3 4h18v16H3zM9 4v16M5 8h2m-2 4h2"/></Glyph> }
export function PanelRight(props: GlyphProps) { return <Glyph {...props}><path d="M3 4h18v16H3zM15 4v16m2 4h2m-2 4h2"/></Glyph> }
export function RotateCcw(props: GlyphProps) { return <Glyph {...props}><path d="M5 9a8 8 0 1 1 1 8M5 4v5h5"/><path d="M12 8v4l3 2"/></Glyph> }
export function Search(props: GlyphProps) { return <Glyph {...props}><circle cx="10" cy="10" r="6"/><path d="m14.5 14.5 6 6M8 10h4m-2-2v4"/></Glyph> }
export function Server(props: GlyphProps) { return <Glyph {...props}><path d="M4 4h16v7H4zM4 13h16v7H4zM8 8h2m-2 9h2m5-9h2m-2 9h2"/></Glyph> }
export function SquareTerminal(props: GlyphProps) { return <Glyph {...props}><path d="M3 4h18v16H3zM7 9l3 3-3 3m6 0h4"/></Glyph> }

export function Command(props: GlyphProps) { return <Glyph {...props}><path d="M7 4h10l3 3v10l-3 3H7l-3-3V7z"/><path d="m8 10 3 3-3 3m6 0h3"/></Glyph> }
export function Rows3(props: GlyphProps) { return <Glyph {...props}><path d="M3 4h18v16H3zM3 9h18M3 15h18M7 6.5h3m-3 5h3m-3 6h3"/></Glyph> }
export function HelpCircle(props: GlyphProps) { return <Glyph {...props}><path d="M12 2 20 7v10l-8 5-8-5V7z"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5m0 3v.5"/></Glyph> }
export { SquareTerminal as TerminalSquare }

// Additional domain-specific pictograms share the same optical stroke system.
export function MaterialPrism(props: GlyphProps) { return <Glyph {...props}><path d="M12 2 21 8v8l-9 6-9-6V8zM12 2v20M3 8l9 6 9-6"/><path d="m7 10 5-3 5 3"/></Glyph> }
export function ParticleHelix(props: GlyphProps) { return <Glyph {...props}><path d="M7 2c13 3-3 7 10 10S4 19 17 22M17 2C4 5 20 9 7 12s13 7 0 10"/><path d="M8 6h8M7 12h10M8 18h8"/></Glyph> }
export function ReflectionField(props: GlyphProps) { return <Glyph {...props}><path d="m12 2 8 8-8 8-8-8zM3 20c3-2 6-2 9 0s6 2 9 0M12 6v8M8 10h8"/></Glyph> }
export function ElectricalArc(props: GlyphProps) { return <Glyph {...props}><path d="m14 2-9 11h7l-2 9 9-12h-7z"/><path d="m3 5 3 2m12 11 3 2"/></Glyph> }
export function TopologyMesh(props: GlyphProps) { return <Glyph {...props}><path d="m12 2 9 6v9l-9 5-9-5V8zM12 2v9l9-3M12 11 3 8m9 3v11M3 17l9-6 9 6"/><circle cx="12" cy="11" r="1"/></Glyph> }
export function ReplayTimeline(props: GlyphProps) { return <Glyph {...props}><path d="M4 8a9 9 0 1 1 0 8M4 3v5h5M12 6v6l4 2"/><path d="M3 21h6"/></Glyph> }


export function Activity(props:GlyphProps){return <Glyph {...props}><path d="M3 12h4l2-6 5 12 3-6h4"/></Glyph>}

export function ArrowLeft(props:GlyphProps){return <Glyph {...props}><path d="m11 5-7 7 7 7M4 12h16"/></Glyph>}

export function ArrowRight(props:GlyphProps){return <Glyph {...props}><path d="m13 5 7 7-7 7M4 12h16"/></Glyph>}

export function Bot(props:GlyphProps){return <Glyph {...props}><path d="M5 7h14v12H5zM12 3v4M9 11v2m6-2v2m-7 3h8M2 10v6m20-6v6"/></Glyph>}

export function Check(props:GlyphProps){return <Glyph {...props}><path d="m5 12 4 5L20 6"/></Glyph>}

export function ChevronDown(props:GlyphProps){return <Glyph {...props}><path d="m5 8 7 8 7-8"/></Glyph>}

export function CircleHelp(props:GlyphProps){return <Glyph {...props}><path d="M12 2 20 7v10l-8 5-8-5V7zM9 9c0-4 6-4 6 0 0 2-3 2-3 5m0 3v.2"/></Glyph>}

export function Clock3(props:GlyphProps){return <Glyph {...props}><path d="M12 2 21 7v10l-9 5-9-5V7zM12 6v6l5 3"/></Glyph>}

export function GitBranch(props:GlyphProps){return <Glyph {...props}><path d="M6 3v18M6 13c0-6 12-2 12-9M3 3h6m-6 18h6m6-17h6"/></Glyph>}

export function Layers3(props:GlyphProps){return <Glyph {...props}><path d="m3 7 9-5 9 5-9 5zM3 12l9 5 9-5M3 17l9 5 9-5"/></Glyph>}

export function Orbit(props:GlyphProps){return <Glyph {...props}><path d="M12 4c11 0 11 16 0 16S1 4 12 4zM4 7c7-9 18 2 16 10S-3 16 4 7zM10 12h4"/></Glyph>}

export function Pause(props:GlyphProps){return <Glyph {...props}><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></Glyph>}

export function Play(props:GlyphProps){return <Glyph {...props}><path d="m7 3 14 9-14 9zM11 9v6"/></Glyph>}

export function ScanEye(props:GlyphProps){return <Glyph {...props}><path d="M3 8V3h5m8 0h5v5M3 16v5h5m8 0h5v-5M5 12l7-4 7 4-7 4z"/></Glyph>}

export function Sparkles(props:GlyphProps){return <Glyph {...props}><path d="m12 2 2 7 7 3-7 2-2 8-2-8-8-2 8-3zM18 3l3 3m-3 0 3-3"/></Glyph>}

export function X(props:GlyphProps){return <Glyph {...props}><path d="m5 5 14 14M19 5 5 19"/></Glyph>}

export function Clipboard(props:GlyphProps){return <Glyph {...props}><path d="M8 5H5v16h14V5h-3M8 3h8v5H8zM8 12h8m-8 4h6"/></Glyph>}

export function Code2(props:GlyphProps){return <Glyph {...props}><path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18"/></Glyph>}

export function CornerDownLeft(props:GlyphProps){return <Glyph {...props}><path d="M20 4v10H4m5-5-5 5 5 5"/></Glyph>}

export function Download(props:GlyphProps){return <Glyph {...props}><path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/></Glyph>}

export function FilePlus2(props:GlyphProps){return <Glyph {...props}><path d="M4 2h10l6 6v14H4zM14 2v6h6M8 15h8m-4-4v8"/></Glyph>}

export function FileText(props:GlyphProps){return <Glyph {...props}><path d="M4 2h10l6 6v14H4zM14 2v6h6M8 12h8m-8 4h8m-8 3h5"/></Glyph>}

export function Image(props:GlyphProps){return <Glyph {...props}><path d="M3 4h18v16H3zM3 17l6-6 5 5 3-3 4 4M7 8h.1"/></Glyph>}

export function LoaderCircle(props:GlyphProps){return <Glyph {...props}><path d="M12 3a9 9 0 1 1-9 9M12 3v4M3 12h4"/></Glyph>}

export function Pencil(props:GlyphProps){return <Glyph {...props}><path d="m4 16 12-12 4 4L8 20H4zM13 7l4 4M4 20l4-4"/></Glyph>}

export function Plus(props:GlyphProps){return <Glyph {...props}><path d="M12 4v16M4 12h16"/></Glyph>}

export function RefreshCw(props:GlyphProps){return <Glyph {...props}><path d="M4 10a8 8 0 0 1 14-5l3 3M21 3v5h-5M20 14a8 8 0 0 1-14 5l-3-3M3 21v-5h5"/></Glyph>}

export function Send(props:GlyphProps){return <Glyph {...props}><path d="m3 3 19 8-10 3-3 8zM12 14 22 11"/></Glyph>}

export function Square(props:GlyphProps){return <Glyph {...props}><path d="M4 4h16v16H4z"/></Glyph>}

export function Trash2(props:GlyphProps){return <Glyph {...props}><path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/></Glyph>}

export function UserRound(props:GlyphProps){return <Glyph {...props}><path d="M9 3h6l2 4-2 4H9L7 7zM4 21v-4l4-3h8l4 3v4"/></Glyph>}

export function VolumeX(props:GlyphProps){return <Glyph {...props}><path d="M3 9h4l5-5v16l-5-5H3zM16 8l6 8m0-8-6 8"/></Glyph>}

export function Blocks(props:GlyphProps){return <Glyph {...props}><path d="M3 3h8v8H3zM13 3h8v8h-8zM3 13h8v8H3zM13 13h8v8h-8z"/></Glyph>}

export function Camera(props:GlyphProps){return <Glyph {...props}><path d="M3 7h5l2-3h4l2 3h5v13H3zM9 13a3 3 0 1 0 6 0 3 3 0 0 0-6 0"/></Glyph>}

export function FileSearch(props:GlyphProps){return <Glyph {...props}><path d="M4 2h10l6 6v14H4zM14 2v6h6M9 12a3 3 0 1 0 6 0 3 3 0 0 0-6 0m5 2 3 4"/></Glyph>}

export function Globe2(props:GlyphProps){return <Glyph {...props}><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20M2 12h20M12 2c7 7 7 13 0 20-7-7-7-13 0-20"/></Glyph>}

export function Library(props:GlyphProps){return <Glyph {...props}><path d="M3 4h4v16H3zM10 4h4v16h-4zM16 5l4-1 3 15-4 1zM4 8h2m5 0h2"/></Glyph>}

export function Mic(props:GlyphProps){return <Glyph {...props}><path d="M9 3h6v10H9zM5 10v3a7 7 0 0 0 14 0v-3M12 20v3M8 23h8"/></Glyph>}

export function Paperclip(props:GlyphProps){return <Glyph {...props}><path d="m8 12 7-7a4 4 0 0 1 6 6L11 21a6 6 0 0 1-8-8L13 3m3 6-9 9"/></Glyph>}

export function WandSparkles(props:GlyphProps){return <Glyph {...props}><path d="m3 18 14-14 3 3L6 21zM6 3l2 2m10 11 3 2M14 2v3"/></Glyph>}

export function CircleDot(props:GlyphProps){return <Glyph {...props}><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20M10 10h4v4h-4z"/></Glyph>}

export function Database(props:GlyphProps){return <Glyph {...props}><path d="M3 5c0-4 18-4 18 0v14c0 4-18 4-18 0zM3 5c0 4 18 4 18 0M3 12c0 4 18 4 18 0"/></Glyph>}

export function ShieldCheck(props:GlyphProps){return <Glyph {...props}><path d="m12 2 9 5-2 10-7 5-7-5L3 7zM7 12l4 4 6-7"/></Glyph>}

export function ChevronRight(props:GlyphProps){return <Glyph {...props}><path d="m8 4 8 8-8 8"/></Glyph>}

export function File(props:GlyphProps){return <Glyph {...props}><path d="M4 2h10l6 6v14H4zM14 2v6h6"/></Glyph>}

export function Maximize2(props:GlyphProps){return <Glyph {...props}><path d="M3 9V3h6M15 3h6v6M3 15v6h6m6 0h6v-6"/></Glyph>}

export function Minimize2(props:GlyphProps){return <Glyph {...props}><path d="M3 9h6V3M15 3v6h6M3 15h6v6m6 0v-6h6"/></Glyph>}
