import { motion } from "framer-motion"

export default function TimelineObservatory() {

  return (
    <div className="h-full p-6">

      <h1 className="text-3xl font-light">
        Timeline Observatory
      </h1>

      <motion.div
        className="mt-10 h-1 bg-white/20"
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
      />

    </div>
  )
}
