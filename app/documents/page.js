'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Plus,
  Trash2,
  Loader2,
  ExternalLink,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  Search,
  Sparkles,
  Eye
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import DesktopSidebar from '@/components/DesktopSidebar'
import MobileNav from '@/components/MobileNav'
import Header from '@/components/Header'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function DocumentsPage() {
  const [files, setFiles] = useState([])
  const [detectedDocs, setDetectedDocs] = useState([])
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newFile, setNewFile] = useState({
    title: '',
    vendor: '',
    doc_type: 'facture',
    keyword: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [filesRes, accountsRes, todayRes] = await Promise.all([
        fetch(`${API_BASE}/api/expected-files`),
        fetch(`${API_BASE}/api/accounts`),
        fetch(`${API_BASE}/api/today`)
      ])

      if (filesRes.ok) {
        const data = await filesRes.json()
        setFiles(data.files || [])
      }
      if (accountsRes.ok) {
        const data = await accountsRes.json()
        setAccounts(data.accounts || [])
      }
      if (todayRes.ok) {
        const data = await todayRes.json()
        setDetectedDocs(data.documents || [])
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const createFile = async () => {
    if (!newFile.vendor) {
      toast.error('Veuillez indiquer un fournisseur')
      return
    }

    setCreating(true)
    try {
      const res = await fetch(`${API_BASE}/api/expected-files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_type: newFile.doc_type,
          vendor: newFile.vendor,
          keyword: newFile.keyword || '',
          due_date: ''
        })
      })

      if (res.ok) {
        toast.success('Document ajouté en surveillance')
        setDialogOpen(false)
        setNewFile({ title: '', vendor: '', doc_type: 'facture', keyword: '' })
        loadData()
      } else {
        const errData = await res.json().catch(() => ({}))
        toast.error(errData.detail || 'Erreur lors de la création')
      }
    } catch (error) {
      console.error('Error creating file:', error)
      toast.error('Erreur réseau')
    } finally {
      setCreating(false)
    }
  }

  const deleteFile = async (fileId) => {
    if (!confirm('Supprimer cette surveillance ?')) return

    try {
      await fetch(`${API_BASE}/api/expected-files/${fileId}`, { method: 'DELETE' })
      toast.success('Surveillance supprimée')
      loadData()
    } catch (error) {
      console.error('Error deleting file:', error)
      toast.error('Erreur lors de la suppression')
    }
  }

  const getStatusConfig = (status) => {
    switch (status) {
      case 'received':
        return { icon: CheckCircle2, label: 'Reçu', color: 'text-green-600', bg: 'bg-green-50' }
      case 'pending':
        return { icon: Clock, label: 'En attente', color: 'text-blue-600', bg: 'bg-blue-50' }
      case 'relanced':
        return { icon: AlertCircle, label: 'Relancé', color: 'text-orange-600', bg: 'bg-orange-50' }
      default:
        return { icon: Clock, label: status, color: 'text-gray-600', bg: 'bg-gray-50' }
    }
  }

  const FileCard = ({ file }) => {
    const status = getStatusConfig(file.status)
    const StatusIcon = status.icon
    // Support both old and new field names
    const docType = file.doc_type || file.file_type
    const vendor = file.vendor || file.contact

    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-card rounded-2xl shadow-sm border border-border/50 overflow-hidden hover:shadow-md transition-shadow"
      >
        <div className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <div className={`p-1.5 rounded-lg ${status.bg}`}>
                  <StatusIcon className={`w-4 h-4 ${status.color}`} />
                </div>
                <h3 className="font-semibold truncate">{file.title}</h3>
              </div>

              <div className="flex flex-wrap gap-2 mb-3">
                <Badge variant="outline" className="text-xs capitalize">
                  {docType}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  {status.label}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Fournisseur</p>
                  <p className="font-medium truncate">{vendor}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Dernière vérification</p>
                  <p className="font-medium">{file.last_check || 'Jamais'}</p>
                </div>
              </div>

              {file.associated_email && (
                <div className="mt-3 p-3 bg-green-50 dark:bg-green-950/20 rounded-xl">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                    <span className="text-sm font-medium text-green-700">Document reçu</span>
                  </div>
                  <p className="text-sm text-muted-foreground truncate">{file.associated_email.subject}</p>
                  <Button variant="link" size="sm" className="p-0 h-auto mt-1" asChild>
                    <a href={file.associated_email.link} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="w-3 h-3 mr-1" />
                      Ouvrir l'email
                    </a>
                  </Button>
                </div>
              )}
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => deleteFile(file.file_id)}
              className="flex-shrink-0 text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </motion.div>
    )
  }

  const DetectedDocCard = ({ doc }) => (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-3 p-3 bg-purple-50 dark:bg-purple-950/20 rounded-xl border-l-4 border-l-purple-500"
    >
      <div className="p-2 bg-purple-100 dark:bg-purple-900/50 rounded-lg">
        <FileText className="w-5 h-5 text-purple-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate capitalize">{doc.type}</p>
        <p className="text-xs text-muted-foreground truncate">{doc.from}</p>
      </div>
      <Badge variant="secondary" className="text-xs flex items-center gap-1">
        <Sparkles className="w-3 h-3" />
        Détecté
      </Badge>
    </motion.div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-purple-50 to-pink-50 dark:from-background dark:via-background dark:to-background">
      <div className="flex h-screen">
        <DesktopSidebar accounts={accounts} />

        <div className="flex-1 flex flex-col overflow-hidden">
          <Header
            title="Documents"
            subtitle="Surveillance et détection automatique"
            rightContent={
              <Button
                onClick={() => setDialogOpen(true)}
                className="gap-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
              >
                <Plus className="w-4 h-4" />
                Surveiller
              </Button>
            }
          />

          <div className="flex-1 overflow-y-auto pb-24 md:pb-6">
            <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-6">
              {loading ? (
                <div className="space-y-4">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-32 bg-white/50 rounded-2xl animate-pulse" />
                  ))}
                </div>
              ) : (
                <>
                  {/* Detected Documents from Recap */}
                  {detectedDocs.length > 0 && (
                    <Card className="border-none shadow-lg overflow-hidden">
                      <CardHeader className="bg-gradient-to-r from-purple-500 to-pink-500 text-white pb-3">
                        <CardTitle className="flex items-center gap-2 text-lg">
                          <Sparkles className="w-5 h-5" />
                          Documents détectés aujourd'hui
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="p-4 space-y-2">
                        {detectedDocs.map((doc, i) => (
                          <DetectedDocCard key={doc.email_id || i} doc={doc} />
                        ))}
                      </CardContent>
                    </Card>
                  )}

                  {/* Quick Add Card */}
                  <Card className="border-none shadow-lg">
                    <CardContent className="p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 bg-purple-100 rounded-xl">
                          <Eye className="w-5 h-5 text-purple-600" />
                        </div>
                        <div>
                          <h3 className="font-semibold">Nouvelle surveillance</h3>
                          <p className="text-sm text-muted-foreground">Ajoutez un document à surveiller</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <Select value={newFile.doc_type} onValueChange={(v) => setNewFile({ ...newFile, doc_type: v })}>
                          <SelectTrigger>
                            <SelectValue placeholder="Type" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="facture">Facture</SelectItem>
                            <SelectItem value="devis">Devis</SelectItem>
                            <SelectItem value="contrat">Contrat</SelectItem>
                            <SelectItem value="attestation">Attestation</SelectItem>
                            <SelectItem value="autre">Autre</SelectItem>
                          </SelectContent>
                        </Select>

                        <Input
                          value={newFile.vendor}
                          onChange={(e) => setNewFile({ ...newFile, vendor: e.target.value })}
                          placeholder="Fournisseur"
                          className="md:col-span-2"
                        />

                        <Button
                          onClick={createFile}
                          disabled={creating || !newFile.vendor}
                          className="gap-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                        >
                          {creating ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Plus className="w-4 h-4" />
                          )}
                          Ajouter
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Watched Files List */}
                  {files.length > 0 ? (
                    <div className="space-y-3">
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Search className="w-5 h-5" />
                        Documents surveillés ({files.length})
                      </h3>
                      {files.map((file, idx) => (
                        <FileCard key={file.file_id || idx} file={file} />
                      ))}
                    </div>
                  ) : (
                    <Card className="border-none shadow-lg">
                      <CardContent className="py-12 text-center">
                        <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-purple-400 to-pink-500 rounded-full flex items-center justify-center">
                          <FileText className="w-8 h-8 text-white" />
                        </div>
                        <h3 className="text-lg font-semibold mb-2">Aucun document surveillé</h3>
                        <p className="text-muted-foreground mb-4 max-w-md mx-auto">
                          Ajoutez une surveillance et l'app vous alertera automatiquement dès qu'un document arrive.
                        </p>
                        <Button
                          onClick={() => setDialogOpen(true)}
                          className="gap-2 bg-gradient-to-r from-purple-500 to-pink-500"
                        >
                          <Plus className="w-4 h-4" />
                          Ajouter une surveillance
                        </Button>
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-purple-600" />
              Nouvelle surveillance
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div>
              <Label>Type de document</Label>
              <Select value={newFile.doc_type} onValueChange={(v) => setNewFile({ ...newFile, doc_type: v })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="facture">Facture</SelectItem>
                  <SelectItem value="devis">Devis</SelectItem>
                  <SelectItem value="contrat">Contrat</SelectItem>
                  <SelectItem value="attestation">Attestation</SelectItem>
                  <SelectItem value="autre">Autre</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Fournisseur *</Label>
              <Input
                value={newFile.vendor}
                onChange={(e) => setNewFile({ ...newFile, vendor: e.target.value })}
                placeholder="Ex: Distram, EDF, Comptable..."
                className="mt-1"
              />
            </div>

            <div>
              <Label>Mot-clé de recherche (optionnel)</Label>
              <Input
                value={newFile.keyword}
                onChange={(e) => setNewFile({ ...newFile, keyword: e.target.value })}
                placeholder="Ex: novembre, ref-12345"
                className="mt-1"
              />
            </div>

            <Button
              onClick={createFile}
              disabled={creating || !newFile.vendor}
              className="w-full gap-2 bg-gradient-to-r from-purple-500 to-pink-500"
            >
              {creating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Plus className="w-4 h-4" />
              )}
              Surveiller ce document
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Mobile FAB */}
      <Button
        onClick={() => setDialogOpen(true)}
        size="icon"
        className="md:hidden fixed bottom-24 right-4 h-14 w-14 rounded-full shadow-lg z-40 bg-gradient-to-r from-purple-500 to-pink-500"
      >
        <Plus className="w-6 h-6" />
      </Button>

      <MobileNav />
    </div>
  )
}
