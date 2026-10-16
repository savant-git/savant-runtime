import GenericObservatory from "./GenericObservatory"

export default function RepositoryObservatory() {
  return (
    <GenericObservatory
      title="Repository Observatory"
      signal="infrastructure / source / code terrain"
      primitives={[
        "source topology",
        "file pressure",
        "change history",
        "module gravity",
        "orphan risk",
        "build surface"
      ]}
    />
  )
}
