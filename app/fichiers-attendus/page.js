'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Plus, Trash2, Loader2, ExternalLink, CheckCircle2, Clock, AlertCircle, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import DesktopSidebar from '@/components/DesktopSidebar'
import MobileNav from '@/components/MobileNav'
import Header from '@/components/Header'
import { useMediaQuery } from '@/hooks/use-mobile'

export default function FichiersAttendusPage() {
  const [files, setFiles] = useState([])
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newFile, setNewFile] = useState({
    title: '',
    contact: '',
    file_type: 'facture',
    keyword: ''
  })
  const isMobile = useMediaQuery('(max-width: 768px)')

  useEffect(() => {
    loadFiles()
    loadAccounts()
  }, [])

  const loadFiles = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/expected-files')
      const data = await res.json()
      setFiles(data.files || [])
    } catch (error) {
      console.error('Erreur chargement fichiers:', error)
    }
  }

  const loadAccounts = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/accounts')
      const data = await res.json()
      setAccounts(data.accounts || [])
    } catch (error) {
      console.error('Erreur chargement comptes:', error)
    }
  }

  const createFile = async () => {
    if (!newFile.contact) {
      toast.error('Veuillez remplir tous les champs')
      return
    }

    try {
      setLoading(true)
      const autoTitle = newFile.title || `${newFile.file_type === 'autre' ? 'Document' : newFile.file_type} - ${newFile.contact}${newFile.keyword ? ` (${newFile.keyword})` : ''}`
      await fetch('http://localhost:8000/api/expected-files', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: autoTitle,
          contact: newFile.contact,
          file_type: newFile.file_type,
          due_date: ''
        })
      })
      toast.success('Fichier attendu créé')
      setDialogOpen(false)
      setNewFile({ title: '', contact: '', file_type: 'facture', keyword: '' })
      loadFiles()
    } catch (error) {
      console.error('Erreur création fichier:', error)
      toast.error('Erreur lors de la création')
    } finally {
      setLoading(false)
    }
  }

  const deleteFile = async (fileId) => {
    if (!confirm('Supprimer ce fichier attendu ?')) return

    try {
      await fetch(`http://localhost:8000/api/expected-files/${fileId}`, { method: 'DELETE' })
      toast.success('Fichier supprimé')
      loadFiles()
    } catch (error) {
      console.error('Erreur suppression fichier:', error)
      toast.error('Erreur lors de la suppression')
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'received':
        return <CheckCircle2 className="w-4 h-4 text-slate-800" />
      case 'pending':
        return <Clock className="w-4 h-4 text-slate-600" />
      case 'relanced':
        return <AlertCircle className="w-4 h-4 text-amber-600" />
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />
    }
  }

  const getStatusLabel = (status) => {
    switch (status) {
      case 'received': return 'Reçu'
      case 'pending': return 'En attente'
      case 'relanced': return 'Relancé'
      default: return status
    }
  }

  const getStatusVariant = (status) => {
    switch (status) {
      case 'received': return 'outline'
      case 'pending': return 'secondary'
      case 'relanced': return 'destructive'
      default: return 'outline'
    }
  }

  const EmptyState = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="text-center py-12 px-4"
    >
      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary/10 flex items-center justify-center">
        <FileText className="w-8 h-8 text-slate-900" />
      </div>
      <h2 className="text-xl md:text-2xl font-bold mb-2 text-slate-900">Aucun document surveillé</h2>
      <p className="text-muted-foreground mb-6 max-w-md mx-auto">
        Ajoute un document (facture, contrat, attestation…) et Inbox Copilot analysera automatiquement tes emails pour te prévenir dès qu’il arrive.
      </p>
    </motion.div>
  )

  const lastCheck = files
    .map((f) => f.last_check)
    .filter(Boolean)
    .sort()
    .reverse()[0]

  return (
    <div className="flex h-screen bg-background">
      <DesktopSidebar accounts={accounts} />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header 
          title="Documents surveillés" 
          subtitle="Inbox Copilot surveille automatiquement tes emails et t’alerte dès qu’un document arrive."
        />

        <div className="flex-1 overflow-auto">
          <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold mb-2">Action rapide</p>
                  <h2 className="text-lg md:text-xl font-semibold text-slate-900">Ajouter un document à surveiller</h2>
                  <p className="text-sm text-slate-600 mt-1">Type, fournisseur, mot-clé : Inbox Copilot s’occupe du reste.</p>
                </div>
                <div className="text-right text-xs text-slate-500">
                  <p className="text-slate-600">Les emails sont analysés automatiquement en arrière-plan.</p>
                  <p className="mt-1">Dernière analyse : {lastCheck || '—'}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <div className="space-y-2">
                  <Label className="text-sm text-slate-700">Type de document</Label>
                  <Select value={newFile.file_type} onValueChange={(v) => setNewFile({...newFile, file_type: v})}>
                    <SelectTrigger className="border-slate-200 focus:ring-indigo-500">
                      <SelectValue placeholder="Choisir un type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="facture">Facture</SelectItem>
                      <SelectItem value="contrat">Contrat</SelectItem>
                      <SelectItem value="autre">Autre</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-slate-700">Fournisseur ou contact</Label>
                  <Input
                    value={newFile.contact}
                    onChange={(e) => setNewFile({...newFile, contact: e.target.value})}
                    placeholder="ex : Distram, Cerfrance"
                    className="border-slate-200 focus:ring-indigo-500 placeholder:text-gray-400"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-slate-700">Mot-clé (optionnel)</Label>
                  <Input
                    value={newFile.keyword}
                    onChange={(e) => setNewFile({...newFile, keyword: e.target.value})}
                    placeholder="ex : facture, devis"
                    className="border-slate-200 focus:ring-indigo-500 placeholder:text-gray-400"
                  />
                </div>
              </div>

              <div className="mt-6 flex flex-wrap items-center gap-3">
                <Button onClick={createFile} disabled={loading} size="lg" className="bg-indigo-600 hover:bg-indigo-700 text-white">
                  {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
                  ➕ Surveiller ce document
                </Button>
                <p className="text-sm text-slate-600">Inbox Copilot surveille et t’alerte dès réception.</p>
              </div>
            </div>

            {files.length === 0 ? (
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-8">
                <EmptyState />
              </div>
            ) : (
              <div className="space-y-3">
                {files.map((file, idx) => (
                  <motion.div
                    key={file.file_id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.03 }}
                  >
                    <Card className="hover:shadow-md transition-shadow border border-slate-200 bg-white">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2 flex-wrap">
                              {getStatusIcon(file.status)}
                              <h3 className="font-semibold truncate text-slate-900">{file.title}</h3>
                              <Badge variant="outline" className="text-xs bg-slate-100 text-slate-800 border-slate-200">{file.file_type}</Badge>
                              <Badge variant={getStatusVariant(file.status)} className="text-xs bg-slate-100 text-slate-800 border-slate-200">
                                {getStatusLabel(file.status)}
                              </Badge>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
                              <div>
                                <p className="text-muted-foreground text-xs">Contact</p>
                                <p className="font-medium text-slate-900">{file.contact}</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground text-xs">Type</p>
                                <p className="font-medium text-slate-900 capitalize">{file.file_type}</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground text-xs">Dernière vérification</p>
                                <p className="font-medium text-slate-900">{file.last_check || '—'}</p>
                              </div>
                            </div>
                            {file.associated_email && (
                              <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
                                <p className="text-sm font-medium text-slate-900 mb-1">📧 Email associé :</p>
                                <p className="text-sm text-slate-700 mb-2 truncate">{file.associated_email.subject}</p>
                                <Button variant="link" size="sm" className="p-0 h-auto text-indigo-700" asChild>
                                  <a href={file.associated_email.link} target="_blank" rel="noopener noreferrer">
                                    <ExternalLink className="w-3 h-3 mr-1" />
                                    Ouvrir l'email
                                  </a>
                                </Button>
                              </div>
                            )}
                          </div>
                          <Button variant="ghost" size="icon" onClick={() => deleteFile(file.file_id)} className="flex-shrink-0 text-slate-500 hover:text-slate-800">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className={cn(isMobile && "max-w-[95%] rounded-lg")}>
          <DialogHeader>
            <DialogTitle>Ajouter un document</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Titre (optionnel)</Label>
              <Input
                value={newFile.title}
                onChange={(e) => setNewFile({...newFile, title: e.target.value})}
                placeholder="Ex: Facture Distram novembre"
                className="placeholder:text-gray-400"
              />
            </div>
            <div>
              <Label>Fournisseur ou contact</Label>
              <Input
                value={newFile.contact}
                onChange={(e) => setNewFile({...newFile, contact: e.target.value})}
                placeholder="Ex: Distram"
                className="placeholder:text-gray-400"
              />
            </div>
            <div>
              <Label>Type de document</Label>
              <Select value={newFile.file_type} onValueChange={(v) => setNewFile({...newFile, file_type: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Choisir" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="facture">Facture</SelectItem>
                  <SelectItem value="contrat">Contrat</SelectItem>
                  <SelectItem value="autre">Autre</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Mot-clé (optionnel)</Label>
              <Input
                value={newFile.keyword}
                onChange={(e) => setNewFile({...newFile, keyword: e.target.value})}
                placeholder="Ex: facture, devis"
                className="placeholder:text-gray-400"
              />
            </div>
            <Button onClick={createFile} disabled={loading} className="w-full" size="lg">
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              ➕ Surveiller ce document
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {isMobile && (
        <Button
          onClick={() => setDialogOpen(true)}
          size="icon"
          className="fixed bottom-20 right-4 h-14 w-14 rounded-full shadow-lg z-40 bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          <Plus className="w-6 h-6" />
        </Button>
      )}

      <MobileNav />
    </div>
  )
}
