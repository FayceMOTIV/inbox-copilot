'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { toast } from 'sonner'
import {
  Bug,
  Server,
  Bell,
  Mail,
  Moon,
  Clock,
  AlertTriangle,
  Copy,
  RefreshCw,
  CheckCircle2,
  XCircle
} from 'lucide-react'
import { getLastApiError, getApiBase } from '@/lib/api-client'

const API_BASE = getApiBase()

// Check if debug mode is enabled (build-time + runtime)
function isDebugEnabled() {
  if (typeof window === 'undefined') return false
  // Build-time check
  const isDev = process.env.NODE_ENV !== 'production'
  const hasBuildFlag = process.env.NEXT_PUBLIC_DEBUG === 'true'
  // Runtime check via URL param (for testing in prod)
  const hasRuntimeFlag = new URLSearchParams(window.location.search).get('debug_key') === 'inbox2024'
  return isDev || hasBuildFlag || hasRuntimeFlag
}

export default function DebugPage() {
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [debugData, setDebugData] = useState({
    version: 'v1.1.2',
    commitHash: null,
    apiBase: API_BASE,
    recaps: { morning: null, evening: null },
    silence: { enabled: false, ranges: [], activeNow: false },
    notifications: { unreadCount: 0 },
    accounts: { count: 0, emails: [] },
    lastError: null,
    health: { backend: false, mongo: false }
  })

  useEffect(() => {
    setMounted(true)

    // Only load debug data if enabled
    if (isDebugEnabled()) {
      loadDebugData()
    }
  }, [])

  const loadDebugData = async () => {
    setLoading(true)

    try {
      // Health check
      let health = { backend: false, mongo: false }
      try {
        const healthRes = await fetch(`${API_BASE}/api/health`)
        if (healthRes.ok) {
          const h = await healthRes.json()
          health = { backend: true, mongo: h.mongo }
        }
      } catch (e) {
        health = { backend: false, mongo: false }
      }

      // Accounts
      let accounts = { count: 0, emails: [] }
      try {
        const accRes = await fetch(`${API_BASE}/api/accounts?user_id=default_user`)
        if (accRes.ok) {
          const data = await accRes.json()
          accounts = {
            count: data.accounts?.length || 0,
            emails: (data.accounts || []).map(a => a.email)
          }
        }
      } catch (e) {}

      // Notifications
      let notifications = { unreadCount: 0 }
      try {
        const notifRes = await fetch(`${API_BASE}/api/notifications?user_id=default_user&limit=1`)
        if (notifRes.ok) {
          const data = await notifRes.json()
          notifications = { unreadCount: data.unread_count || 0 }
        }
      } catch (e) {}

      // Silence mode
      let silence = { enabled: false, ranges: [], activeNow: false }
      try {
        const silenceRes = await fetch(`${API_BASE}/api/memory/silence?user_id=default_user`)
        if (silenceRes.ok) {
          const data = await silenceRes.json()
          silence = {
            enabled: data.enabled || false,
            ranges: data.ranges || [],
            activeNow: data.active_now || false
          }
        }
      } catch (e) {}

      // Recaps
      let recaps = { morning: null, evening: null }
      try {
        const recapsRes = await fetch(`${API_BASE}/api/recaps?user_id=default_user&limit=2`)
        if (recapsRes.ok) {
          const data = await recapsRes.json()
          const list = data.recaps || []
          const morning = list.find(r => r.type === 'morning')
          const evening = list.find(r => r.type === 'evening')
          recaps = {
            morning: morning?.created_at || null,
            evening: evening?.created_at || null
          }
        }
      } catch (e) {}

      // Last API error
      const lastError = getLastApiError()

      setDebugData(prev => ({
        ...prev,
        health,
        accounts,
        notifications,
        silence,
        recaps,
        lastError
      }))
    } catch (e) {
      console.error('Debug load error:', e)
    } finally {
      setLoading(false)
    }
  }

  const copyFeedback = () => {
    const feedback = `=== Inbox Copilot Debug Report ===
Timestamp: ${new Date().toISOString()}
URL: ${typeof window !== 'undefined' ? window.location.href : 'N/A'}
UserAgent: ${typeof navigator !== 'undefined' ? navigator.userAgent : 'N/A'}
Version: ${debugData.version}

Backend: ${debugData.apiBase}
Health: Backend=${debugData.health.backend}, Mongo=${debugData.health.mongo}

Accounts: ${debugData.accounts.count} (${debugData.accounts.emails.join(', ') || 'none'})
Notifications Unread: ${debugData.notifications.unreadCount}

Silence Mode: ${debugData.silence.enabled ? 'ON' : 'OFF'}
Silence Active Now: ${debugData.silence.activeNow ? 'YES' : 'NO'}
Silence Ranges: ${JSON.stringify(debugData.silence.ranges)}

Last Recap Morning: ${debugData.recaps.morning || 'none'}
Last Recap Evening: ${debugData.recaps.evening || 'none'}

Last API Error: ${debugData.lastError ? JSON.stringify(debugData.lastError) : 'none'}
===================================`

    navigator.clipboard.writeText(feedback)
    toast.success('Debug info copied!')
  }

  // Don't render on server or if not mounted
  if (!mounted) {
    return null
  }

  // Show 404-like page if debug not enabled
  if (!isDebugEnabled()) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
          <p className="text-muted-foreground mt-2">Page not found</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-amber-100 dark:bg-amber-950/50">
              <Bug className="w-6 h-6 text-amber-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Debug Panel</h1>
              <p className="text-sm text-muted-foreground">DEV ONLY - v1.1.2</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadDebugData}
              disabled={loading}
              className="rounded-full"
            >
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              onClick={copyFeedback}
              className="rounded-full bg-gradient-to-r from-amber-500 to-orange-500"
            >
              <Copy className="w-4 h-4 mr-1" />
              Copy Feedback
            </Button>
          </div>
        </div>

        {/* Version & Backend */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Server className="w-4 h-4" />
                Backend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground mb-2">API Base URL</p>
              <code className="text-sm bg-muted px-2 py-1 rounded">{debugData.apiBase}</code>
              <div className="flex gap-2 mt-3">
                <Badge variant={debugData.health.backend ? 'default' : 'destructive'}>
                  {debugData.health.backend ? <CheckCircle2 className="w-3 h-3 mr-1" /> : <XCircle className="w-3 h-3 mr-1" />}
                  API
                </Badge>
                <Badge variant={debugData.health.mongo ? 'default' : 'destructive'}>
                  {debugData.health.mongo ? <CheckCircle2 className="w-3 h-3 mr-1" /> : <XCircle className="w-3 h-3 mr-1" />}
                  MongoDB
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Accounts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{debugData.accounts.count}</p>
              <p className="text-xs text-muted-foreground">Connected accounts</p>
              {debugData.accounts.emails.length > 0 && (
                <div className="mt-2 space-y-1">
                  {debugData.accounts.emails.map((email, i) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {email}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Notifications & Silence */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Bell className="w-4 h-4" />
                Notifications
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{debugData.notifications.unreadCount}</p>
              <p className="text-xs text-muted-foreground">Unread notifications</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Moon className="w-4 h-4" />
                Silence Mode
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant={debugData.silence.enabled ? 'default' : 'secondary'}>
                  {debugData.silence.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
                {debugData.silence.activeNow && (
                  <Badge className="bg-purple-500">Active Now</Badge>
                )}
              </div>
              {debugData.silence.ranges.length > 0 && (
                <div className="text-xs text-muted-foreground">
                  Ranges: {debugData.silence.ranges.map(r => `${r.start}-${r.end}`).join(', ')}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recaps */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Last Recaps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Morning</p>
                <p className="text-sm font-medium">
                  {debugData.recaps.morning
                    ? new Date(debugData.recaps.morning).toLocaleString('fr-FR')
                    : 'None'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Evening</p>
                <p className="text-sm font-medium">
                  {debugData.recaps.evening
                    ? new Date(debugData.recaps.evening).toLocaleString('fr-FR')
                    : 'None'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Last API Error */}
        <Card className={debugData.lastError ? 'border-red-500' : ''}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              Last API Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            {debugData.lastError ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="destructive">{debugData.lastError.status || 'ERR'}</Badge>
                  <code className="text-xs bg-muted px-2 py-1 rounded">
                    {debugData.lastError.endpoint}
                  </code>
                </div>
                <p className="text-sm text-red-600">{debugData.lastError.message}</p>
                <p className="text-xs text-muted-foreground">
                  {debugData.lastError.timestamp}
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No errors captured</p>
            )}
          </CardContent>
        </Card>

        {/* Back button */}
        <Button
          variant="outline"
          onClick={() => router.push('/')}
          className="rounded-full"
        >
          Back to Assistant
        </Button>
      </div>
    </div>
  )
}
