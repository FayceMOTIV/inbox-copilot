'use client'

import { MessageSquare, Sun, Calendar, FileText, Settings, Brain } from 'lucide-react'
import { usePathname, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import Logo from '@/components/Logo'

export default function DesktopSidebar({ accounts = [] }) {
  const pathname = usePathname()
  const router = useRouter()

  const navItems = [
    { icon: MessageSquare, label: 'Assistant', path: '/' },
    { icon: Sun, label: "Aujourd'hui", path: '/aujourdhui' },
    { icon: Calendar, label: 'Récaps', path: '/recaps' },
    { icon: FileText, label: 'Documents', path: '/documents' },
  ]

  const secondaryItems = [
    { icon: Brain, label: 'Mémoire', path: '/memoire' },
    { icon: Settings, label: 'Paramètres', path: '/parametres' },
  ]

  const NavButton = ({ item }) => {
    const Icon = item.icon
    const isActive = pathname === item.path
    return (
      <Button
        variant={isActive ? "default" : "ghost"}
        className={cn(
          "w-full justify-start rounded-xl transition-all",
          isActive && "bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg shadow-blue-500/25"
        )}
        onClick={() => router.push(item.path)}
      >
        <Icon className="w-4 h-4 mr-3" />
        {item.label}
      </Button>
    )
  }

  return (
    <div className="hidden md:flex w-64 border-r border-border glass p-4 flex-col">
      <div className="mb-8 px-2">
        <Logo size="md" showText />
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map((item) => (
          <NavButton key={item.path} item={item} />
        ))}
      </nav>

      <Separator className="my-4" />

      <nav className="space-y-1 mb-4">
        {secondaryItems.map((item) => (
          <NavButton key={item.path} item={item} />
        ))}
      </nav>

      <div className="flex items-center gap-3 p-2 bg-muted/50 rounded-xl">
        <Avatar className="w-9 h-9">
          <AvatarFallback className="bg-gradient-to-r from-blue-500 to-purple-600 text-white">U</AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">Utilisateur</p>
          <p className="text-xs text-muted-foreground">{accounts.length} compte{accounts.length !== 1 ? 's' : ''}</p>
        </div>
      </div>
    </div>
  )
}
