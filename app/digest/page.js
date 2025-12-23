'use client'

import { useState, useEffect } from 'react'
import {
  AlertCircle,
  FileText,
  Clock,
  RefreshCw,
  Mail,
  ExternalLink,
  ChevronRight,
  Calendar,
  TrendingUp,
  Inbox,
  CheckCircle2
} from 'lucide-react'
import Header from '@/components/Header'
import DesktopSidebar from '@/components/DesktopSidebar'
import MobileNav from '@/components/MobileNav'
import AccountSelector from '@/components/AccountSelector'
import NotificationCenter from '@/components/NotificationCenter'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function DigestPage() {
  const [accounts, setAccounts] = useState([])
  const [selectedAccountId, setSelectedAccountId] = useState(null)
  const [digest, setDigest] = useState(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)

  // Fetch accounts
  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/accounts`)
        if (res.ok) {
          const data = await res.json()
          setAccounts(data.accounts || [])
        }
      } catch (error) {
        console.error('Error fetching accounts:', error)
      }
    }
    fetchAccounts()
  }, [])

  // Fetch latest digest
  useEffect(() => {
    const fetchLatestDigest = async () => {
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE}/api/digest/latest`)
        if (res.ok) {
          const data = await res.json()
          setDigest(data)
        }
      } catch (error) {
        console.error('Error fetching digest:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchLatestDigest()
  }, [])

  const generateDigest = async () => {
    setGenerating(true)
    try {
      const body = {
        days_back: 1,
        accounts: selectedAccountId ? [selectedAccountId] : null
      }
      const res = await fetch(`${API_BASE}/api/digest/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      if (res.ok) {
        const data = await res.json()
        setDigest(data)
        toast.success('Digest généré avec succès')
      } else {
        toast.error('Erreur lors de la génération')
      }
    } catch (error) {
      console.error('Error generating digest:', error)
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

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'urgent':
        return <Badge variant="destructive" className="text-xs">Urgent</Badge>
      case 'important':
        return <Badge variant="default" className="text-xs bg-orange-500">Important</Badge>
      default:
        return <Badge variant="secondary" className="text-xs">Info</Badge>
    }
  }

  const EmailCard = ({ item, type }) => (
    <div className="p-3 bg-background rounded-lg border border-border/50 hover:border-border transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {getPriorityBadge(item.priority || type)}
            <span className="text-xs text-muted-foreground truncate">
              {item.from || item.from_email}
            </span>
          </div>
          <h4 className="font-medium text-sm truncate">{item.subject}</h4>
          <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
            {item.snippet}
          </p>
        </div>
        {item.has_attachments && (
          <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        )}
      </div>
      {item.link && (
        <a
          href={item.link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-primary mt-2 hover:underline"
        >
          Ouvrir <ExternalLink className="w-3 h-3" />
        </a>
      )}
    </div>
  )

  const WaitingCard = ({ item }) => (
    <div className="p-3 bg-background rounded-lg border border-border/50">
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-sm truncate">{item.subject || 'Sans sujet'}</span>
        {item.is_overdue && (
          <Badge variant="destructive" className="text-xs">En retard</Badge>
        )}
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Clock className="w-3 h-3" />
        <span>En attente depuis {item.days_waiting || 0} jour(s)</span>
      </div>
    </div>
  )

  const StatCard = ({ icon: Icon, label, value, color }) => (
    <div className="flex items-center gap-3 p-3 bg-background rounded-lg border border-border/50">
      <div className={`p-2 rounded-full ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <div className="text-2xl font-bold">{value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-[#F7F8FB] dark:bg-background">
      {/* Desktop Sidebar */}
      <div className="hidden md:block fixed left-0 top-0 h-full w-20 z-50">
        <DesktopSidebar />
      </div>

      {/* Main Content */}
      <div className="md:ml-20 pb-20 md:pb-0">
        <Header
          title="Digest"
          subtitle={digest?.date ? formatDate(digest.date) : "Résumé de vos emails"}
          rightContent={
            <div className="flex items-center gap-2">
              <AccountSelector
                accounts={accounts}
                selectedAccountId={selectedAccountId}
                onSelect={setSelectedAccountId}
                showAllOption={true}
              />
              <NotificationCenter />
            </div>
          }
        />

        <div className="p-4 md:p-6 max-w-6xl mx-auto">
          {/* Generate Button */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-xl font-semibold">Votre digest quotidien</h1>
              <p className="text-sm text-muted-foreground">
                {digest?.generated_at
                  ? `Dernière mise à jour: ${new Date(digest.generated_at).toLocaleString('fr-FR')}`
                  : 'Générez votre premier digest'}
              </p>
            </div>
            <Button
              onClick={generateDigest}
              disabled={generating}
              className="gap-2"
            >
              {generating ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Générer
            </Button>
          </div>

          {/* Stats Overview */}
          {digest?.stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              <StatCard
                icon={AlertCircle}
                label="Urgents"
                value={digest.stats.urgent_count}
                color="bg-red-100 text-red-600"
              />
              <StatCard
                icon={TrendingUp}
                label="Importants"
                value={digest.stats.important_count}
                color="bg-orange-100 text-orange-600"
              />
              <StatCard
                icon={Clock}
                label="En attente"
                value={digest.stats.waiting_count}
                color="bg-blue-100 text-blue-600"
              />
              <StatCard
                icon={Inbox}
                label="Total scannés"
                value={digest.stats.total_scanned}
                color="bg-gray-100 text-gray-600"
              />
            </div>
          )}

          {loading ? (
            <div className="space-y-4">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : digest ? (
            <div className="grid md:grid-cols-3 gap-4">
              {/* Urgent Column */}
              <Card className="border-red-200 bg-red-50/30 dark:bg-red-950/10">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-red-600">
                    <AlertCircle className="w-5 h-5" />
                    Urgents
                  </CardTitle>
                  <CardDescription>
                    {digest.urgent?.length || 0} email(s) nécessitant une action immédiate
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {digest.urgent?.length > 0 ? (
                    digest.urgent.map((item, i) => (
                      <EmailCard key={item.email_id || i} item={item} type="urgent" />
                    ))
                  ) : (
                    <div className="text-center py-4 text-sm text-muted-foreground">
                      <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-green-500" />
                      Aucun email urgent
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Important Column */}
              <Card className="border-orange-200 bg-orange-50/30 dark:bg-orange-950/10">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-orange-600">
                    <TrendingUp className="w-5 h-5" />
                    Importants
                  </CardTitle>
                  <CardDescription>
                    {digest.important?.length || 0} email(s) à traiter aujourd'hui
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {digest.important?.length > 0 ? (
                    digest.important.map((item, i) => (
                      <EmailCard key={item.email_id || i} item={item} type="important" />
                    ))
                  ) : (
                    <div className="text-center py-4 text-sm text-muted-foreground">
                      Aucun email important
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Waiting Column */}
              <Card className="border-blue-200 bg-blue-50/30 dark:bg-blue-950/10">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-blue-600">
                    <Clock className="w-5 h-5" />
                    En attente
                  </CardTitle>
                  <CardDescription>
                    {digest.waiting?.length || 0} conversation(s) sans réponse
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {digest.waiting?.length > 0 ? (
                    digest.waiting.map((item, i) => (
                      <WaitingCard key={item.thread_id || i} item={item} />
                    ))
                  ) : (
                    <div className="text-center py-4 text-sm text-muted-foreground">
                      Aucune conversation en attente
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card className="text-center py-12">
              <CardContent>
                <Calendar className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-medium mb-2">Pas encore de digest</h3>
                <p className="text-muted-foreground mb-4">
                  Cliquez sur "Générer" pour créer votre premier résumé quotidien
                </p>
                <Button onClick={generateDigest} disabled={generating}>
                  {generating ? 'Génération...' : 'Générer maintenant'}
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Mobile Nav */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50">
        <MobileNav />
      </div>
    </div>
  )
}
