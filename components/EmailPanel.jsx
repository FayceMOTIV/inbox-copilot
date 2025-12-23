'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Download, Reply, Forward, ExternalLink, Paperclip,
  FileText, Image, File, Loader2, Check, ChevronDown, ChevronUp,
  Mail, Calendar, User, CheckCircle2, Clock
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

// File type icon and color mapping
const getFileInfo = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (['pdf'].includes(ext)) return { icon: FileText, color: 'text-red-500', bg: 'bg-red-50' }
  if (['xlsx', 'xls', 'csv'].includes(ext)) return { icon: FileText, color: 'text-green-600', bg: 'bg-green-50' }
  if (['doc', 'docx'].includes(ext)) return { icon: FileText, color: 'text-blue-600', bg: 'bg-blue-50' }
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return { icon: Image, color: 'text-purple-500', bg: 'bg-purple-50' }
  return { icon: File, color: 'text-gray-500', bg: 'bg-gray-50' }
}

const formatFileSize = (bytes) => {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

export default function EmailPanel({
  email,
  attachments = [],
  accountId,
  onClose,
  onReply,
  onDownloadComplete,
  isOpen,
  multiEmailMode = false,
  emailsWithAttachments = []
}) {
  const [downloading, setDownloading] = useState(false)
  const [downloadComplete, setDownloadComplete] = useState(false)
  const [downloadedFiles, setDownloadedFiles] = useState([])

  if (!email && !multiEmailMode) return null

  // Filter out image signatures (small images)
  const realAttachments = attachments.filter(att => {
    const isImage = att.mimeType?.startsWith('image/')
    const isSmall = att.size < 50000 // Less than 50KB
    const isSignature = att.filename?.toLowerCase().includes('image00')
    return !(isImage && isSmall) && !isSignature
  })

  // Download a single file to browser using fetch + blob
  const downloadFile = async (att) => {
    try {
      // Use the email_id from attachment if available (multi-email mode), otherwise use email.id
      const emailId = att.email_id || email?.id
      const url = `${API_BASE_URL}/api/email/${emailId}/attachment/${encodeURIComponent(att.attachmentId)}?account_id=${accountId}`

      // Fetch the file as a blob
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const blob = await response.blob()

      // Create a blob URL and trigger download
      const blobUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = att.filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      // Clean up the blob URL
      window.URL.revokeObjectURL(blobUrl)

      return att.filename
    } catch (error) {
      console.error(`Error downloading ${att.filename}:`, error)
      throw error
    }
  }

  const handleDownloadAll = async () => {
    if (!accountId || !email.id) {
      toast.error('Impossible de télécharger')
      return
    }

    setDownloading(true)
    const downloaded = []

    try {
      // Download each file with a small delay to not overwhelm the browser
      for (const att of realAttachments) {
        try {
          await downloadFile(att)
          downloaded.push(att.filename)
          setDownloadedFiles([...downloaded])
        } catch (e) {
          console.error(`Failed to download ${att.filename}`)
        }
        // Small delay between downloads
        await new Promise(r => setTimeout(r, 300))
      }

      setDownloadComplete(true)
      toast.success(`${downloaded.length} fichier(s) téléchargé(s)`, {
        description: 'Vérifiez votre dossier Téléchargements'
      })
      onDownloadComplete?.(downloaded)
    } catch (error) {
      console.error('Download error:', error)
      toast.error('Erreur lors du téléchargement')
    } finally {
      setDownloading(false)
    }
  }

  // Download single file
  const handleDownloadSingle = async (att) => {
    try {
      await downloadFile(att)
      setDownloadedFiles(prev => [...prev, att.filename])
      toast.success(`${att.filename} téléchargé`)
    } catch (error) {
      toast.error(`Erreur: ${att.filename}`)
    }
  }

  const handleOpenInGmail = () => {
    if (email.link) {
      window.open(email.link, '_blank')
    } else if (email.id) {
      window.open(`https://mail.google.com/mail/u/0/#inbox/${email.id}`, '_blank')
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
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 w-full md:w-[500px] lg:w-[600px] bg-white dark:bg-gray-900 shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="p-4 md:p-6 border-b border-gray-200 dark:border-gray-800">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  {multiEmailMode ? (
                    // Multi-email mode header
                    <>
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white font-bold">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900 dark:text-white">
                            Téléchargement groupé
                          </p>
                          <p className="text-xs text-gray-500">{emailsWithAttachments.length} emails sélectionnés</p>
                        </div>
                      </div>
                      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
                        {realAttachments.length} fichiers à télécharger
                      </h2>
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <Paperclip className="w-4 h-4" />
                        <span>{formatFileSize(realAttachments.reduce((acc, a) => acc + (a.size || 0), 0))} au total</span>
                      </div>
                    </>
                  ) : (
                    // Single email mode header
                    <>
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                          {(email?.from_name || email?.from || '?')[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900 dark:text-white">
                            {email?.from_name || email?.from?.split('<')[0]?.trim() || 'Expéditeur inconnu'}
                          </p>
                          <p className="text-xs text-gray-500">{email?.from_email}</p>
                        </div>
                      </div>
                      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
                        {email?.subject || 'Sans objet'}
                      </h2>
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <Clock className="w-4 h-4" />
                        <span>{formatDate(email?.date)}</span>
                      </div>
                    </>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onClose}
                  className="rounded-full shrink-0 hover:bg-gray-100"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden flex flex-col">
              {/* Email Preview or Multi-email list */}
              {multiEmailMode ? (
                <div className="p-4 md:p-6 border-b border-gray-200 dark:border-gray-800 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Emails inclus :
                  </p>
                  <div className="space-y-1">
                    {emailsWithAttachments.slice(0, 5).map((e, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <Mail className="w-3 h-3" />
                        <span className="truncate">{e.subject}</span>
                        <Badge variant="outline" className="text-xs ml-auto shrink-0">
                          {e.attachments?.length || 0} PJ
                        </Badge>
                      </div>
                    ))}
                    {emailsWithAttachments.length > 5 && (
                      <p className="text-xs text-gray-500">
                        + {emailsWithAttachments.length - 5} autres emails...
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-4 md:p-6 border-b border-gray-200 dark:border-gray-800">
                  <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                    {email?.snippet || email?.body || 'Aucun aperçu disponible'}
                  </p>
                </div>
              )}

              {/* Attachments Section - THE MAIN FEATURE */}
              {realAttachments.length > 0 && (
                <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-800/50">
                  <div className="p-4 md:p-6 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                          <Paperclip className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <h3 className="font-bold text-gray-900 dark:text-white">
                            {realAttachments.length} Pièce{realAttachments.length > 1 ? 's' : ''} jointe{realAttachments.length > 1 ? 's' : ''}
                          </h3>
                          <p className="text-sm text-gray-500">
                            {formatFileSize(realAttachments.reduce((acc, a) => acc + (a.size || 0), 0))} au total
                          </p>
                        </div>
                      </div>

                      <Button
                        onClick={handleDownloadAll}
                        disabled={downloading}
                        className={cn(
                          "rounded-xl gap-2 px-6",
                          downloadComplete
                            ? "bg-green-500 hover:bg-green-600"
                            : "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                        )}
                      >
                        {downloading ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Téléchargement...
                          </>
                        ) : downloadComplete ? (
                          <>
                            <CheckCircle2 className="w-4 h-4" />
                            Téléchargé
                          </>
                        ) : (
                          <>
                            <Download className="w-4 h-4" />
                            Tout télécharger
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* File List */}
                  <ScrollArea className="flex-1">
                    <div className="p-4 md:p-6 space-y-3">
                      {realAttachments.map((att, idx) => {
                        const fileInfo = getFileInfo(att.filename)
                        const FileIcon = fileInfo.icon
                        const isDownloaded = downloadedFiles.includes(att.filename)

                        return (
                          <motion.div
                            key={idx}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            onClick={() => handleDownloadSingle(att)}
                            className={cn(
                              "flex items-center gap-4 p-4 rounded-xl bg-white dark:bg-gray-800 border-2 transition-all cursor-pointer",
                              isDownloaded
                                ? "border-green-200 dark:border-green-800"
                                : "border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-md"
                            )}
                          >
                            <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center", fileInfo.bg)}>
                              <FileIcon className={cn("w-6 h-6", fileInfo.color)} />
                            </div>

                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-gray-900 dark:text-white truncate">
                                {att.filename}
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline" className="text-xs">
                                  {att.filename.split('.').pop()?.toUpperCase()}
                                </Badge>
                                <span className="text-xs text-gray-500">
                                  {formatFileSize(att.size)}
                                </span>
                              </div>
                            </div>

                            {isDownloaded ? (
                              <div className="flex items-center gap-1 text-green-600">
                                <CheckCircle2 className="w-5 h-5" />
                                <span className="text-sm font-medium">OK</span>
                              </div>
                            ) : (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="shrink-0 rounded-full hover:bg-blue-50 hover:text-blue-600"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleDownloadSingle(att)
                                }}
                              >
                                <Download className="w-5 h-5" />
                              </Button>
                            )}
                          </motion.div>
                        )
                      })}
                    </div>
                  </ScrollArea>
                </div>
              )}

              {/* No attachments message */}
              {realAttachments.length === 0 && (
                <div className="flex-1 flex items-center justify-center p-8">
                  <div className="text-center text-gray-500">
                    <Paperclip className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p>Aucune pièce jointe</p>
                  </div>
                </div>
              )}
            </div>

            {/* Footer Actions */}
            <div className="p-4 md:p-6 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
              {multiEmailMode ? (
                // Multi-email mode: just close button
                <Button
                  variant="outline"
                  onClick={onClose}
                  className="w-full rounded-xl gap-2"
                >
                  <X className="w-4 h-4" />
                  Fermer
                </Button>
              ) : (
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={() => onReply?.(email)}
                    className="flex-1 rounded-xl gap-2"
                  >
                    <Reply className="w-4 h-4" />
                    Répondre
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleOpenInGmail}
                    className="flex-1 rounded-xl gap-2"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Ouvrir dans Gmail
                  </Button>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
