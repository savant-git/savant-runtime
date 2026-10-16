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
