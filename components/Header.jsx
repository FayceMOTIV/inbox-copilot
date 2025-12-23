'use client'

import { Moon, Sun, MoonStar } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Header({ title, subtitle, rightContent }) {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [silenceEnabled, setSilenceEnabled] = useState(false)
  const [loadingSilence, setLoadingSilence] = useState(false)

  useEffect(() => {
    setMounted(true)
    loadSilenceStatus()
  }, [])

  const loadSilenceStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/silence?user_id=default_user`)
      if (res.ok) {
        const data = await res.json()
        setSilenceEnabled(data.enabled)
      }
    } catch (error) {
      console.error('Error loading silence status:', error)
    }
  }

  const toggleSilence = async () => {
    setLoadingSilence(true)
    try {
      const res = await fetch(`${API_BASE}/api/settings/silence?user_id=default_user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !silenceEnabled })
      })
      if (res.ok) {
        const data = await res.json()
        setSilenceEnabled(data.enabled)
        toast.success(data.enabled ? 'Mode silence activé' : 'Mode silence désactivé')
      }
    } catch (error) {
      console.error('Error toggling silence:', error)
      toast.error('Erreur')
    } finally {
      setLoadingSilence(false)
    }
  }

  return (
    <div className="border-b border-border bg-card/80 backdrop-blur-xl sticky top-0 z-40">
      <div className="flex items-center justify-between h-16 px-4 md:px-6">
        <div className="flex items-center gap-3">
          {title && (
            <div>
              <h2 className="text-lg md:text-xl font-semibold text-[#2F2F2F]">{title}</h2>
              {subtitle && (
                <p className="text-xs md:text-sm text-[#6B7280]">{subtitle}</p>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {rightContent}
          {mounted && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleSilence}
                    disabled={loadingSilence}
                    className={`rounded-full transition-colors ${
                      silenceEnabled
                        ? 'bg-indigo-100 text-indigo-600 hover:bg-indigo-200 dark:bg-indigo-900/50 dark:text-indigo-400'
                        : ''
                    }`}
                  >
                    <MoonStar className={`w-5 h-5 ${silenceEnabled ? 'fill-current' : ''}`} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-medium">Mode Silence</p>
                  {silenceEnabled ? (
                    <p className="text-xs text-muted-foreground">Actif: 11h-14h, 18h-00h</p>
                  ) : (
                    <p className="text-xs text-muted-foreground">Désactivé</p>
                  )}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="rounded-full"
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
