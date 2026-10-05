import { motion } from "framer-motion"

export function AmbientField() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {[...Array(18)].map((_,i)=>(
        <motion.div
          key={i}
          className="absolute rounded-full"
          style={{
            width:2 + (i % 5),
            height:2 + (i % 5),
            left:`${(i*7)%100}%`,
            top:`${(i*13)%100}%`,
            background:"rgba(255,255,255,.08)"
          }}
          animate={{
            y:[0,-60,0],
            x:[0,20,-20,0]
          }}
          transition={{
            repeat:Infinity,
            duration:20 + i
          }}
        />
      ))}
    </div>
  )
}
