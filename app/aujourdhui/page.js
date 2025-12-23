'use client'

import { useState, useEffect } from 'react'
import {
  AlertCircle,
  FileText,
  Clock,
  RefreshCw,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Star,
  Zap
} from 'lucide-react'
import Header from '@/components/Header'
import DesktopSidebar from '@/components/DesktopSidebar'
import MobileNav from '@/components/MobileNav'
import NotificationCenter from '@/components/NotificationCenter'
import EmailDrawer from '@/components/EmailDrawer'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { motion } from 'framer-motion'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function AujourdhuiPage() {
  const [data, setData] = useState(null)
  const [recap, setRecap] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const fetchData = async (showToast = false) => {
    try {
      if (showToast) setRefreshing(true)
      const [todayRes, recapRes] = await Promise.all([
        fetch(`${API_BASE}/api/today`),
        fetch(`${API_BASE}/api/recap/auto`)
      ])
      if (todayRes.ok) {
        const result = await todayRes.json()
        setData(result)
      }
      if (recapRes.ok) {
        const result = await recapRes.json()
        setRecap(result)
      }
      if (showToast) toast.success('Actualisé')
    } catch (error) {
      console.error('Error fetching data:', error)
      if (showToast) toast.error('Erreur')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const openEmail = (email) => {
    setSelectedEmail(email)
    setDrawerOpen(true)
  }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Bonjour'
    if (hour < 18) return 'Bon après-midi'
    return 'Bonsoir'
  }

  const suggestions = recap?.suggestions || []
  const urgent = data?.urgent || recap?.urgent || []
  const todo = data?.todo || recap?.todo || []
  const waiting = data?.waiting || recap?.waiting || []
  const documents = data?.documents || recap?.documents || []

  const ActionCard = ({ suggestion, index }) => (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-2xl border border-blue-200 dark:border-blue-800 hover:shadow-lg transition-all cursor-pointer"
      onClick={() => {
        if (suggestion.email_id) {
          const email = [...urgent, ...todo].find(e => e.email_id === suggestion.email_id)
          if (email) openEmail(email)
        }
      }}
    >
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{suggestion.action}</p>
          <p className="text-xs text-muted-foreground">{suggestion.reason}</p>
        </div>
        <ArrowRight className="w-4 h-4 text-muted-foreground" />
      </div>
    </motion.div>
  )

  const EmailCard = ({ item, priority, onClick }) => (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className={`p-4 rounded-xl border-l-4 cursor-pointer transition-all hover:shadow-md ${
        priority === 'urgent' ? 'border-l-red-500 bg-red-50 dark:bg-red-950/20' :
        priority === 'todo' ? 'border-l-orange-500 bg-orange-50 dark:bg-orange-950/20' :
        'border-l-blue-500 bg-blue-50 dark:bg-blue-950/20'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {item.is_vip && (
              <Badge className="bg-gradient-to-r from-amber-500 to-orange-500 text-white border-none text-xs">
                <Star className="w-3 h-3 mr-0.5" />VIP
              </Badge>
            )}
            <span className="text-sm text-muted-foreground truncate">
              {item.from?.split('<')[0]?.trim() || item.from_email}
            </span>
            {item.has_attachments && (
              <FileText className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            )}
          </div>
          <h4 className="font-semibold text-sm truncate">{item.subject}</h4>
          <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            {item.reason}
          </p>
        </div>
      </div>
    </motion.div>
  )

  const WaitingCard = ({ item, onClick }) => (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/20 border-l-4 border-l-blue-500 cursor-pointer hover:shadow-md transition-all"
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-sm truncate flex-1">{item.subject || 'Sans sujet'}</span>
        {item.is_overdue && (
          <Badge variant="destructive" className="text-xs ml-2">Relance</Badge>
        )}
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Clock className="w-3 h-3" />
        <span>{item.days_waiting || 0} jour{(item.days_waiting || 0) !== 1 ? 's' : ''} sans réponse</span>
      </div>
    </motion.div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 dark:from-background dark:via-background dark:to-background">
      <div className="flex h-screen">
        <DesktopSidebar />

        <div className="flex-1 flex flex-col overflow-hidden">
          <Header
            title={getGreeting()}
            subtitle={new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
            rightContent={
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fetchData(true)}
                  disabled={refreshing}
                  className="gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                </Button>
                <NotificationCenter />
              </div>
            }
          />

          <div className="flex-1 overflow-y-auto pb-24 md:pb-6">
            <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-6">
              {loading ? (
                <div className="space-y-4">
                  <Skeleton className="h-24 rounded-2xl" />
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-2xl" />)}
                  </div>
                </div>
              ) : (
                <>
                  {/* Top Actions */}
                  {suggestions.length > 0 && (
                    <Card className="border-none shadow-lg overflow-hidden">
                      <CardHeader className="bg-gradient-to-r from-blue-500 to-purple-600 text-white pb-3">
                        <CardTitle className="flex items-center gap-2 text-lg">
                          <Zap className="w-5 h-5" />
                          Actions recommandées
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="p-4 space-y-2">
                        {suggestions.slice(0, 3).map((s, i) => (
                          <ActionCard key={i} suggestion={s} index={i} />
                        ))}
                      </CardContent>
                    </Card>
                  )}

                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="p-4 bg-gradient-to-br from-red-500 to-rose-600 rounded-2xl text-white">
                      <AlertCircle className="w-6 h-6 mb-2 opacity-80" />
                      <div className="text-3xl font-bold">{data?.stats?.urgent_count || urgent.length}</div>
                      <div className="text-sm opacity-80">Urgents</div>
                    </motion.div>
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="p-4 bg-gradient-to-br from-orange-500 to-amber-600 rounded-2xl text-white">
                      <TrendingUp className="w-6 h-6 mb-2 opacity-80" />
                      <div className="text-3xl font-bold">{data?.stats?.todo_count || todo.length}</div>
                      <div className="text-sm opacity-80">À traiter</div>
                    </motion.div>
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="p-4 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-2xl text-white">
                      <Clock className="w-6 h-6 mb-2 opacity-80" />
                      <div className="text-3xl font-bold">{data?.stats?.waiting_count || waiting.length}</div>
                      <div className="text-sm opacity-80">En attente</div>
                    </motion.div>
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="p-4 bg-gradient-to-br from-purple-500 to-violet-600 rounded-2xl text-white">
                      <FileText className="w-6 h-6 mb-2 opacity-80" />
                      <div className="text-3xl font-bold">{documents.length}</div>
                      <div className="text-sm opacity-80">Documents</div>
                    </motion.div>
                  </div>

                  {/* Urgent Section */}
                  {urgent.length > 0 && (
                    <Card className="border-none shadow-lg">
                      <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-red-600">
                          <AlertCircle className="w-5 h-5" />
                          Actions urgentes
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {urgent.slice(0, 5).map((item, i) => (
                          <EmailCard key={item.email_id || i} item={item} priority="urgent" onClick={() => openEmail(item)} />
                        ))}
                      </CardContent>
                    </Card>
                  )}

                  {/* Todo Section */}
                  {todo.length > 0 && (
                    <Card className="border-none shadow-lg">
                      <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-orange-600">
                          <TrendingUp className="w-5 h-5" />
                          À traiter
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {todo.slice(0, 5).map((item, i) => (
                          <EmailCard key={item.email_id || i} item={item} priority="todo" onClick={() => openEmail(item)} />
                        ))}
                      </CardContent>
                    </Card>
                  )}

                  {/* Waiting Section */}
                  {waiting.length > 0 && (
                    <Card className="border-none shadow-lg">
                      <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-blue-600">
                          <Clock className="w-5 h-5" />
                          En attente de réponse
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {waiting.map((item, i) => (
                          <WaitingCard key={item.thread_id || i} item={item} onClick={() => openEmail(item)} />
                        ))}
                      </CardContent>
                    </Card>
                  )}

                  {/* Empty State */}
                  {!urgent.length && !todo.length && !waiting.length && !suggestions.length && (
                    <Card className="border-none shadow-lg">
                      <CardContent className="py-12 text-center">
                        <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center">
                          <CheckCircle2 className="w-8 h-8 text-white" />
                        </div>
                        <h3 className="text-lg font-semibold mb-2">Tout est en ordre !</h3>
                        <p className="text-muted-foreground">Aucune action urgente pour le moment.</p>
                      </CardContent>
                    </Card>
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
        onStatusChange={() => fetchData(true)}
      />

      <MobileNav />
    </div>
  )
}
