'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  ExternalLink,
  Star,
  Clock,
  CheckCircle2,
  FileText,
  Download,
  UserPlus,
  Loader2,
  Sparkles
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function EmailDrawer({
  email,
  isOpen,
  onClose,
  onStatusChange,
  onVipAdded
}) {
  const [loading, setLoading] = useState(null)

  if (!email) return null

  const handleMarkDone = async () => {
    setLoading('done')
    try {
      const res = await fetch(`${API_BASE}/api/threads/${email.thread_id || email.email_id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'DONE' })
      })
      if (res.ok) {
        toast.success('Marqué comme traité')
        onStatusChange?.('done')
        onClose()
      } else {
        const errData = await res.json().catch(() => ({}))
        toast.error(errData.detail || 'Erreur lors du marquage')
      }
    } catch (error) {
      console.error('handleMarkDone error:', error)
      toast.error('Erreur réseau')
    } finally {
      setLoading(null)
    }
  }

  const handleMarkWaiting = async () => {
    setLoading('waiting')
    try {
      const res = await fetch(`${API_BASE}/api/threads/${email.thread_id || email.email_id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'WAITING' })
      })
      if (res.ok) {
        toast.success('Mis en attente')
        onStatusChange?.('waiting')
        onClose()
      } else {
        const errData = await res.json().catch(() => ({}))
        toast.error(errData.detail || 'Erreur lors du marquage')
      }
    } catch (error) {
      console.error('handleMarkWaiting error:', error)
      toast.error('Erreur réseau')
    } finally {
      setLoading(null)
    }
  }

  const handleAddVip = async () => {
    setLoading('vip')
    try {
      const fromEmail = email.from_email || email.from?.match(/<(.+)>/)?.[1] || email.from
      const label = email.from?.split('<')[0]?.trim() || fromEmail

      const res = await fetch(`${API_BASE}/api/memory/vips`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label, email: fromEmail })
      })
      if (res.ok) {
        toast.success(`${label} ajouté aux VIP`)
        onVipAdded?.()
      } else {
        const errData = await res.json().catch(() => ({}))
        toast.error(errData.detail || 'Erreur lors de l\'ajout VIP')
      }
    } catch (error) {
      console.error('handleAddVip error:', error)
      toast.error('Erreur réseau')
    } finally {
      setLoading(null)
    }
  }

  const handleAddDocRule = async () => {
    setLoading('doc')
    try {
      const fromEmail = email.from_email || email.from
      const vendorName = email.from?.split('<')[0]?.trim() || 'Fournisseur'

      const res = await fetch(`${API_BASE}/api/expected-files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_type: 'facture',
          vendor: vendorName,
          keyword: '',
          due_date: ''
        })
      })
      if (res.ok) {
        toast.success('Règle de surveillance créée')
      } else {
        const errData = await res.json().catch(() => ({}))
        toast.error(errData.detail || 'Erreur lors de la création')
      }
    } catch (error) {
      console.error('handleAddDocRule error:', error)
      toast.error('Erreur réseau')
    } finally {
      setLoading(null)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('fr-FR', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 z-50"
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-white dark:bg-card shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <div className="flex items-center gap-2">
                {email.is_vip && (
                  <Badge className="bg-gradient-to-r from-amber-500 to-orange-500 text-white border-none">
                    <Star className="w-3 h-3 mr-1" />
                    VIP
                  </Badge>
                )}
                {email.priority === 'urgent' && (
                  <Badge variant="destructive">Urgent</Badge>
                )}
                {email.priority === 'todo' && (
                  <Badge className="bg-orange-500 text-white">À traiter</Badge>
                )}
              </div>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Subject */}
              <div>
                <h2 className="text-lg font-bold leading-tight">{email.subject || 'Sans sujet'}</h2>
              </div>

              {/* From */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                  {(email.from || 'U')[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{email.from?.split('<')[0]?.trim() || email.from_email}</p>
                  <p className="text-sm text-muted-foreground truncate">{email.from_email}</p>
                </div>
              </div>

              {/* Date */}
              <div className="text-sm text-muted-foreground">
                {formatDate(email.date)}
              </div>

              {/* Reason */}
              {email.reason && (
                <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-xl">
                  <Sparkles className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-700 dark:text-blue-400">
                    {email.reason}
                  </span>
                </div>
              )}

              {/* Snippet */}
              <div className="p-4 bg-muted/50 rounded-xl">
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {email.snippet || 'Pas d\'aperçu disponible'}
                </p>
              </div>

              {/* Attachments indicator */}
              {email.has_attachments && (
                <div className="flex items-center gap-2 p-3 bg-purple-50 dark:bg-purple-950/30 rounded-xl">
                  <FileText className="w-4 h-4 text-purple-600" />
                  <span className="text-sm font-medium text-purple-700 dark:text-purple-400">
                    Contient des pièces jointes
                  </span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-4 border-t space-y-3">
              {/* Primary actions */}
              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={handleMarkDone}
                  disabled={loading === 'done'}
                  className="gap-2 bg-gradient-to-r from-green-500 to-emerald-600"
                >
                  {loading === 'done' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4" />
                  )}
                  Traité
                </Button>
                <Button
                  onClick={handleMarkWaiting}
                  disabled={loading === 'waiting'}
                  variant="outline"
                  className="gap-2"
                >
                  {loading === 'waiting' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Clock className="w-4 h-4" />
                  )}
                  En attente
                </Button>
              </div>

              {/* Secondary actions */}
              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={handleAddVip}
                  disabled={loading === 'vip' || email.is_vip}
                  variant="outline"
                  className="gap-2"
                >
                  {loading === 'vip' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Star className="w-4 h-4" />
                  )}
                  {email.is_vip ? 'Déjà VIP' : 'Ajouter VIP'}
                </Button>
                <Button
                  onClick={handleAddDocRule}
                  disabled={loading === 'doc'}
                  variant="outline"
                  className="gap-2"
                >
                  {loading === 'doc' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <FileText className="w-4 h-4" />
                  )}
                  Surveiller
                </Button>
              </div>

              {/* Open in Gmail */}
              {email.link && (
                <Button variant="secondary" className="w-full gap-2" asChild>
                  <a href={email.link} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="w-4 h-4" />
                    Ouvrir dans Gmail
                  </a>
                </Button>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
