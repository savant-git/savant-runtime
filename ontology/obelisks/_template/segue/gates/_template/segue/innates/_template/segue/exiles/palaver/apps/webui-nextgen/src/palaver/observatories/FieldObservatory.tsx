import { useApi } from "../hooks/useApi"

type FieldRow = {
  id: string
  label: string
  kind: string
  authority_mass: number
  dependency_pressure: number
  relationship_density: number
  recovery_priority: number
  uncertainty_fog: number
}

type Payload = {
  generated_at?: string
  count?: number
  fields?: FieldRow[]
}

export default function FieldObservatory() {
  const { data, error } = useApi<Payload>(
    "/api/observatory/fields",
    { fields: [] }
  )

  const rows = (data.fields || []).slice(0, 36)

  return (
    <section className="field-observatory">
      <header className="field-header">
        <p>structural perception layer</p>
        <h1>Structural Fields</h1>
        <span>{data.count || rows.length} measured entities</span>
      </header>

      {error && (
        <div className="field-error">
          backend unavailable: {error}
        </div>
      )}

      <div className="field-grid">
        {rows.map((row) => (
          <article className="field-card" key={row.id}>
            <div className="field-card-top">
              <strong>{row.label}</strong>
              <span>{row.kind}</span>
            </div>

            <div className="field-meter">
              <i style={{ width: `${Math.min(row.authority_mass, 100)}%` }} />
            </div>

            <div className="field-stats">
              <span>A {row.authority_mass}</span>
              <span>D {row.dependency_pressure}</span>
              <span>R {row.relationship_density}</span>
              <span>U {row.uncertainty_fog}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
