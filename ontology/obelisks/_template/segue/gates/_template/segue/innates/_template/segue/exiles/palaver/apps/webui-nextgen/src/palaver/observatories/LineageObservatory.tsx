import GenericObservatory from "./GenericObservatory"

export default function LineageObservatory() {
  return (
    <GenericObservatory
      title="Lineage Observatory"
      signal="ancestry / mutation / recovery"
      primitives={[
        "origin",
        "inheritance",
        "mutation",
        "supersession",
        "restore path",
        "historical strata"
      ]}
    />
  )
}
