'use client'

import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'

export default function Logo({ size = 'md', animated = true, showText = false }) {
  const sizes = {
    sm: { container: 40, icon: 24, text: 'text-lg' },
    md: { container: 64, icon: 36, text: 'text-2xl' },
    lg: { container: 80, icon: 48, text: 'text-3xl' },
    xl: { container: 120, icon: 72, text: 'text-4xl' }
  }

  const { container, icon, text } = sizes[size]

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 15 }}
      className="flex items-center gap-3"
    >
      <motion.div
        whileHover={animated ? { scale: 1.08, rotate: 3 } : undefined}
        whileTap={animated ? { scale: 0.95 } : undefined}
        className="relative cursor-pointer"
        style={{ width: container, height: container }}
      >
        {/* Glow effect */}
        <motion.div 
          animate={animated ? {
            scale: [1, 1.15, 1],
            opacity: [0.25, 0.4, 0.25]
          } : undefined}
          transition={{
            duration: 2.5,
            repeat: Infinity,
            ease: 'easeInOut'
          }}
          className="absolute inset-0 rounded-3xl"
          style={{
            background: 'linear-gradient(135deg, #0066FF 0%, #7C3AED 50%, #FF6B35 100%)',
            filter: 'blur(20px)'
          }}
        />
        
        {/* Main container */}
        <div 
          className="relative w-full h-full rounded-3xl flex items-center justify-center shadow-xl overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, #0066FF 0%, #7C3AED 50%, #FF6B35 100%)'
          }}
        >
          {/* Shine effect */}
          <div className="absolute inset-0 shine" />
          
          {/* Zap Icon */}
          <motion.div
            animate={animated ? {
              rotate: [0, -8, 8, -8, 0],
              scale: [1, 1.08, 1]
            } : undefined}
            transition={{
              duration: 2,
              repeat: Infinity,
              repeatDelay: 3,
              ease: 'easeInOut'
            }}
          >
            <Zap 
              size={icon} 
              className="text-white drop-shadow-lg" 
              fill="white"
              strokeWidth={1.5}
            />
          </motion.div>
        </div>
      </motion.div>
      
      {showText && (
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h1 className={`${text} font-black gradient-text`}>
            Inbox Copilot
          </h1>
          <p className="text-sm text-readable-muted font-semibold">Propulsé par IA</p>
        </motion.div>
      )}
    </motion.div>
  )
}