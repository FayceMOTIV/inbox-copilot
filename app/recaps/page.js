'use client'

import { useState, useEffect } from 'react'
import {
  Sun,
  Moon,
  Calendar,
  RefreshCw,
  AlertCircle,
  TrendingUp,
  Clock,
  FileText,
  ChevronRight,
  Sparkles,
  Bell,
  Star,
  ArrowRight
} from 'lucide-react'
import Header from '@/components/Header'
import DesktopSidebar from '@/components/DesktopSidebar'
import MobileNav from '@/components/MobileNav'
import EmailDrawer from '@/components/EmailDrawer'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from 'sonner'
import { motion } from 'framer-motion'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function RecapsPage() {
  const [currentRecap, setCurrentRecap] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [activeTab, setActiveTab] = useState('auto')
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const openEmail = (email) => {
    setSelectedEmail(email)
    setDrawerOpen(true)
  }

  const fetchCurrentRecap = async (type = 'auto') => {
    try {
      const res = await fetch(`${API_BASE}/api/recap/${type}`)
      if (res.ok) {
        const data = await res.json()
        setCurrentRecap(data)
      }
    } catch (error) {
      console.error('Error fetching recap:', error)
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/recaps/history?limit=14`)
      if (res.ok) {
        const data = await res.json()
        setHistory(data.recaps || [])
      }
    } catch (error) {
      console.error('Error fetching history:', error)
    }
  }

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([fetchCurrentRecap(), fetchHistory()])
      setLoading(false)
    }
    loadData()
  }, [])

  const generateRecap = async (type) => {
    setGenerating(true)
    try {
      const res = await fetch(`${API_BASE}/api/recap/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, force: true })
      })
      if (res.ok) {
        const data = await res.json()
        setCurrentRecap(data)
        await fetchHistory()
        toast.success('Récap généré avec succès')
      } else {
        toast.error('Erreur lors de la génération')
      }
    } catch (error) {
      console.error('Error generating recap:', error)
      toast.error('Erreur de connexion')
    } finally {
      setGenerating(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long'
    })
  }

  const formatTime = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getRecapIcon = (type) => {
    switch (type) {
      case 'morning': return Sun
      case 'evening': return Moon
      default: return Calendar
    }
  }

  const getRecapLabel = (type) => {
    switch (type) {
      case 'morning': return 'Matin'
      case 'evening': return 'Soir'
      default: return 'Manuel'
    }
  }

  const getRecapGradient = (type) => {
    switch (type) {
      case 'morning': return 'from-amber-500 to-orange-500'
      case 'evening': return 'from-indigo-500 to-purple-600'
      default: return 'from-blue-500 to-cyan-500'
    }
  }

  const RecapCard = ({ recap, isMain = false }) => {
    const Icon = getRecapIcon(recap.type)
    const gradient = getRecapGradient(recap.type)
    const isEvening = recap.type === 'evening'

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-2xl overflow-hidden ${isMain ? 'shadow-xl' : 'shadow-md'}`}
      >
        {/* Header with gradient */}
        <div className={`bg-gradient-to-r ${gradient} p-4 text-white`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-xl">
                <Icon className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-lg">Récap {getRecapLabel(recap.type)}</h3>
                <p className="text-white/80 text-sm">{formatDate(recap.date)}</p>
              </div>
            </div>
            {recap.generated_at && (
              <Badge variant="secondary" className="bg-white/20 text-white border-none">
                {formatTime(recap.generated_at)}
              </Badge>
            )}
          </div>
          {/* Summary sentence */}
          {recap.summary && (
            <p className="mt-3 text-white/90 text-sm">{recap.summary}</p>
          )}
        </div>

        {/* Stats */}
        <div className="bg-white dark:bg-card p-4 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center p-3 bg-red-50 dark:bg-red-950/20 rounded-xl">
              <div className="text-2xl font-bold text-red-600">{recap.stats?.urgent_count || 0}</div>
              <div className="text-xs text-muted-foreground">Urgents</div>
            </div>
            <div className="text-center p-3 bg-orange-50 dark:bg-orange-950/20 rounded-xl">
              <div className="text-2xl font-bold text-orange-600">{recap.stats?.todo_count || 0}</div>
              <div className="text-xs text-muted-foreground">À traiter</div>
            </div>
            <div className="text-center p-3 bg-blue-50 dark:bg-blue-950/20 rounded-xl">
              <div className="text-2xl font-bold text-blue-600">{recap.stats?.waiting_count || 0}</div>
              <div className="text-xs text-muted-foreground">En attente</div>
            </div>
          </div>

          {/* Urgent emails section */}
          {isMain && recap.urgent?.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-2 text-red-600">
                <AlertCircle className="w-4 h-4" />
                Urgents ({recap.urgent.length})
              </h4>
              {recap.urgent.slice(0, 3).map((item, i) => (
                <div
                  key={item.email_id || i}
                  className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-950/20 rounded-xl cursor-pointer hover:shadow-md transition-all"
                  onClick={() => openEmail(item)}
                >
                  {item.is_vip && (
                    <Badge className="bg-gradient-to-r from-amber-500 to-orange-500 text-white border-none text-xs">
                      <Star className="w-3 h-3 mr-0.5" />VIP
                    </Badge>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{item.subject}</p>
                    <p className="text-xs text-muted-foreground truncate">{item.from?.split('<')[0]?.trim()}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                </div>
              ))}
            </div>
          )}

          {/* TODO emails section */}
          {isMain && recap.todo?.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-2 text-orange-600">
                <TrendingUp className="w-4 h-4" />
                À traiter ({recap.todo.length})
              </h4>
              {recap.todo.slice(0, 3).map((item, i) => (
                <div
                  key={item.email_id || i}
                  className="flex items-center gap-3 p-3 bg-orange-50 dark:bg-orange-950/20 rounded-xl cursor-pointer hover:shadow-md transition-all"
                  onClick={() => openEmail(item)}
                >
                  {item.is_vip && (
                    <Badge className="bg-gradient-to-r from-amber-500 to-orange-500 text-white border-none text-xs">
                      <Star className="w-3 h-3 mr-0.5" />VIP
                    </Badge>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{item.subject}</p>
                    <p className="text-xs text-muted-foreground truncate">{item.from?.split('<')[0]?.trim()}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                </div>
              ))}
            </div>
          )}

          {/* Waiting section */}
          {isMain && recap.waiting?.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-2 text-blue-600">
                <Clock className="w-4 h-4" />
                En attente ({recap.waiting.length})
              </h4>
              {recap.waiting.slice(0, 3).map((item, i) => (
                <div
                  key={item.thread_id || i}
                  className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-950/20 rounded-xl cursor-pointer hover:shadow-md transition-all"
                  onClick={() => openEmail(item)}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{item.subject || 'Sans sujet'}</p>
                    <p className="text-xs text-muted-foreground">{item.days_waiting || 0} jour{(item.days_waiting || 0) !== 1 ? 's' : ''} sans réponse</p>
                  </div>
                  {item.is_overdue && (
                    <Badge variant="destructive" className="text-xs">Relance</Badge>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Documents section */}
          {isMain && recap.documents?.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-2 text-purple-600">
                <FileText className="w-4 h-4" />
                Documents ({recap.documents.length})
              </h4>
              {recap.documents.slice(0, 3).map((item, i) => (
                <div
                  key={item.email_id || i}
                  className="flex items-center gap-3 p-3 bg-purple-50 dark:bg-purple-950/20 rounded-xl cursor-pointer hover:shadow-md transition-all"
                  onClick={() => openEmail(item)}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{item.subject}</p>
                    <p className="text-xs text-muted-foreground truncate">{item.doc_type || 'Document'}</p>
                  </div>
                  <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                </div>
              ))}
            </div>
          )}

          {/* Rappels IA (evening only) */}
          {isMain && isEvening && recap.rappels_ia?.length > 0 && (
            <div className="space-y-2 mt-4 pt-4 border-t">
              <h4 className="text-sm font-semibold flex items-center gap-2 text-indigo-600">
                <Bell className="w-4 h-4" />
                Rappels IA
              </h4>
              {recap.rappels_ia.map((rappel, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 p-3 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/20 dark:to-purple-950/20 rounded-xl cursor-pointer hover:shadow-md transition-all"
                  onClick={() => {
                    if (rappel.email_id) {
                      const email = [...(recap.urgent || []), ...(recap.todo || []), ...(recap.waiting || [])].find(e => e.email_id === rappel.email_id || e.thread_id === rappel.email_id)
                      if (email) openEmail(email)
                    }
                  }}
                >
                  <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{rappel.message}</p>
                    {rappel.context && (
                      <p className="text-xs text-muted-foreground">{rappel.context}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Suggestions */}
          {isMain && recap.suggestions?.length > 0 && (
            <div className="space-y-2 mt-4 pt-4 border-t">
              <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
                <Sparkles className="w-4 h-4" />
                Actions recommandées
              </h4>
              {recap.suggestions.slice(0, 3).map((suggestion, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 p-3 bg-muted/50 rounded-xl cursor-pointer hover:bg-muted transition-all"
                  onClick={() => {
                    if (suggestion.email_id) {
                      const email = [...(recap.urgent || []), ...(recap.todo || [])].find(e => e.email_id === suggestion.email_id)
                      if (email) openEmail(email)
                    }
                  }}
                >
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{suggestion.action}</p>
                    <p className="text-xs text-muted-foreground">{suggestion.reason}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    )
  }

  const HistoryItem = ({ recap }) => {
    const Icon = getRecapIcon(recap.type)
    return (
      <div className="flex items-center gap-4 p-3 bg-white dark:bg-card rounded-xl shadow-sm">
        <div className={`p-2 rounded-lg bg-gradient-to-br ${getRecapGradient(recap.type)}`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">{formatDate(recap.date)}</p>
          <p className="text-xs text-muted-foreground">{getRecapLabel(recap.type)} - {formatTime(recap.generated_at)}</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-red-600 font-medium">{recap.stats?.urgent_count || 0}</span>
          <span className="text-muted-foreground">/</span>
          <span className="text-orange-600 font-medium">{recap.stats?.todo_count || 0}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-indigo-50 to-purple-50 dark:from-background dark:via-background dark:to-background">
      <div className="flex h-screen">
        <DesktopSidebar />

        <div className="flex-1 flex flex-col overflow-hidden">
          <Header
            title="Récaps"
            subtitle="Vos résumés matin et soir"
            rightContent={
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => generateRecap('morning')}
                  disabled={generating}
                  className="gap-2"
                >
                  <Sun className="w-4 h-4" />
                  Matin
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => generateRecap('evening')}
                  disabled={generating}
                  className="gap-2"
                >
                  <Moon className="w-4 h-4" />
                  Soir
                </Button>
              </div>
            }
          />

          <div className="flex-1 overflow-y-auto pb-24 md:pb-6">
            <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
              {loading ? (
                <div className="space-y-4">
                  <Skeleton className="h-64 rounded-2xl" />
                  <Skeleton className="h-16 rounded-xl" />
                  <Skeleton className="h-16 rounded-xl" />
                </div>
              ) : (
                <>
                  {/* Current Recap */}
                  {currentRecap && !currentRecap.error ? (
                    <RecapCard recap={currentRecap} isMain={true} />
                  ) : (
                    <Card className="border-none shadow-lg">
                      <CardContent className="py-12 text-center">
                        <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center">
                          <Calendar className="w-8 h-8 text-white" />
                        </div>
                        <h3 className="text-lg font-semibold mb-2">Pas encore de récap</h3>
                        <p className="text-muted-foreground mb-4">
                          Générez votre premier récap du jour
                        </p>
                        <div className="flex gap-2 justify-center">
                          <Button
                            onClick={() => generateRecap('morning')}
                            disabled={generating}
                            className="gap-2 bg-gradient-to-r from-amber-500 to-orange-500"
                          >
                            <Sun className="w-4 h-4" />
                            Récap Matin
                          </Button>
                          <Button
                            onClick={() => generateRecap('evening')}
                            disabled={generating}
                            className="gap-2 bg-gradient-to-r from-indigo-500 to-purple-600"
                          >
                            <Moon className="w-4 h-4" />
                            Récap Soir
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* History */}
                  {history.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Calendar className="w-5 h-5" />
                        Historique
                      </h3>
                      <div className="space-y-2">
                        {history.slice(0, 10).map((recap, i) => (
                          <HistoryItem key={recap.id || i} recap={recap} />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <EmailDrawer
        email={selectedEmail}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onStatusChange={() => fetchCurrentRecap()}
      />

      <MobileNav />
    </div>
  )
}
