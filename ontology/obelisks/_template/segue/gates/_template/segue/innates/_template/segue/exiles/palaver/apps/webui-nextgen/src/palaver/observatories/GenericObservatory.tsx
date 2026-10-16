import { motion } from "framer-motion"

type Props = {
  title: string
  signal: string
  primitives: string[]
}

export default function GenericObservatory({
  title,
  signal,
  primitives
}: Props) {
  return (
    <section className="observatory">
      <header className="observatory-header">
        <p>{signal}</p>
        <h1>{title}</h1>
      </header>

      <div className="observatory-grid">
        {primitives.map((item, index) => (
          <motion.article
            className="observatory-tile"
            key={item}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.035 }}
          >
            <span>{item}</span>
            <div className="tile-line" />
          </motion.article>
        ))}
      </div>
    </section>
  )
}
