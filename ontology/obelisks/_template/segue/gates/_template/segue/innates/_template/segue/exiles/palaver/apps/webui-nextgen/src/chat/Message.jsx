import { motion } from "framer-motion"

export default function Message({ role, children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18, scale: .985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 220, damping: 24 }}
      className={"message " + role}
    >
      <div className="message-header">
        {role === "user" ? "YOU" : "PALAVER"}
      </div>

      <div className="message-body">
        {children}
      </div>
    </motion.div>
  )
}
