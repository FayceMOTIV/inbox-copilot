'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const messages = [
  "Tu parles, je gère tes mails. Recherche, réponses, relances — je m'occupe de tout.",
  "Ton temps est précieux. Laisse-moi dompter ta boîte mail.",
  "Moins d'emails, plus de business. 🚀"
]

export default function MotivationalMessage() {
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % messages.length)
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative h-16 flex items-center justify-center overflow-hidden">
      <AnimatePresence mode="wait">
        <motion.p
          key={currentIndex}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.5 }}
          className="text-base md:text-lg text-[#111827] text-center px-4 max-w-2xl"
        >
          {messages[currentIndex]}
        </motion.p>
      </AnimatePresence>
    </div>
  )
}
