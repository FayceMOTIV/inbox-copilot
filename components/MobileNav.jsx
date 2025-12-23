'use client'

import { MessageSquare, Sun, Calendar, FileText } from 'lucide-react'
import { usePathname, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

export default function MobileNav() {
  const pathname = usePathname()
  const router = useRouter()

  const navItems = [
    { icon: MessageSquare, label: 'Assistant', path: '/' },
    { icon: Sun, label: "Aujourd'hui", path: '/aujourdhui' },
    { icon: Calendar, label: 'Récaps', path: '/recaps' },
    { icon: FileText, label: 'Documents', path: '/documents' },
  ]

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 glass border-t border-border z-50 safe-area-bottom">
      <div className="flex items-center justify-around h-20 px-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.path
          return (
            <motion.button
              key={item.path}
              whileTap={{ scale: 0.9 }}
              onClick={() => router.push(item.path)}
              className={cn(
                "flex flex-col items-center justify-center flex-1 h-14 rounded-2xl transition-all relative",
                isActive && "bg-gradient-to-r from-blue-500 to-purple-600 shadow-lg shadow-blue-500/25"
              )}
            >
              <Icon className={cn(
                "w-6 h-6 mb-0.5 transition-all",
                isActive ? "text-white" : "text-muted-foreground"
              )} />
              <span className={cn(
                "text-xs font-medium",
                isActive ? "text-white" : "text-muted-foreground"
              )}>{item.label}</span>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
