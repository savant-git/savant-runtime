import GenericObservatory from "./GenericObservatory"

export default function DependencyObservatory() {
  return (
    <GenericObservatory
      title="Dependency Observatory"
      signal="pressure / tension / collapse risk"
      primitives={[
        "critical paths",
        "fault lines",
        "dependency currents",
        "bottlenecks",
        "single points",
        "stability fields"
      ]}
    />
  )
}
