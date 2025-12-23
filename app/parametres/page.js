'use client'

import { useState, useEffect, Suspense } from 'react'
import { motion } from 'framer-motion'
import { Plus, Trash2, Loader2, CheckCircle2, Mail, BellOff, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { useRouter, useSearchParams } from 'next/navigation'
import DesktopSidebar from '@/components/DesktopSidebar'
import MobileNav from '@/components/MobileNav'
import Header from '@/components/Header'
import { useMediaQuery } from '@/hooks/use-mobile'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

function ParametresContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [accounts, setAccounts] = useState([])
  const [signatures, setSignatures] = useState([])
  const [loading, setLoading] = useState(false)
  const [newSignature, setNewSignature] = useState({ name: '', content: '', account_id: '', is_default: false })
  const [signatureDialogOpen, setSignatureDialogOpen] = useState(false)
  const [gmailConnected, setGmailConnected] = useState(false)
  const [memoryStats, setMemoryStats] = useState({ contacts: 0, aliases: 0, vendors: 0 })
  const [aliases, setAliases] = useState([])
  const [vendors, setVendors] = useState([])
  const [loadingMemory, setLoadingMemory] = useState(false)
  const [silenceSettings, setSilenceSettings] = useState({
    enabled: false,
    ranges: [
      { start: '11:00', end: '14:00' },
      { start: '18:00', end: '23:59' }
    ]
  })
  const [loadingSilence, setLoadingSilence] = useState(false)
  const isMobile = useMediaQuery('(max-width: 768px)')

  useEffect(() => {
    loadAccounts()
    loadSignatures()
    loadMemory()
    loadSilenceSettings()

    const success = searchParams.get('success')
    const error = searchParams.get('error')
    const gmailConnected = searchParams.get('gmail')
    if (success) {
      toast.success(`Compte ${success} connecté avec succès !`)
      loadAccounts()
    }
    if (gmailConnected === 'connected') {
      toast.success('Gmail connecté ✅')
      setGmailConnected(true)
      loadAccounts()
    }
    if (error) {
      toast.error(`Erreur lors de la connexion ${error}`)
    }
  }, [searchParams])

  const loadAccounts = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/accounts`)
      const data = await res.json()
      setAccounts(data.accounts || [])
      const gmail = (data.accounts || []).find(acc => acc.provider === 'gmail')
      setGmailConnected(!!gmail)
    } catch (error) {
      console.error('Erreur chargement comptes:', error)
    }
  }

  const loadSignatures = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/signatures`)
      const data = await res.json()
      setSignatures(data.signatures || [])
    } catch (error) {
      console.error('Erreur chargement signatures:', error)
    }
  }

  const loadMemory = async () => {
    setLoadingMemory(true)
    try {
      const [statsRes, aliasesRes, vendorsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/memory/stats?user_id=default_user`),
        fetch(`${API_BASE_URL}/api/memory/aliases?user_id=default_user&limit=10`),
        fetch(`${API_BASE_URL}/api/memory/vendors?user_id=default_user&limit=10`)
      ])
      const statsData = await statsRes.json()
      const aliasesData = await aliasesRes.json()
      const vendorsData = await vendorsRes.json()
      setMemoryStats(statsData.stats || { contacts: 0, aliases: 0, vendors: 0 })
      setAliases(aliasesData.aliases || [])
      setVendors(vendorsData.vendors || [])
    } catch (error) {
      console.error('Erreur chargement mémoire:', error)
    } finally {
      setLoadingMemory(false)
    }
  }

  const loadSilenceSettings = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/settings/silence?user_id=default_user`)
      if (res.ok) {
        const data = await res.json()
        setSilenceSettings(data)
      }
    } catch (error) {
      console.error('Erreur chargement mode silence:', error)
    }
  }

  const updateSilenceSettings = async (newSettings) => {
    setLoadingSilence(true)
    try {
      const res = await fetch(`${API_BASE_URL}/api/settings/silence?user_id=default_user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings)
      })
      if (res.ok) {
        const data = await res.json()
        setSilenceSettings(data)
        toast.success(newSettings.enabled ? 'Mode silence activé' : 'Mode silence désactivé')
      }
    } catch (error) {
      console.error('Erreur mise à jour mode silence:', error)
      toast.error('Erreur lors de la mise à jour')
    } finally {
      setLoadingSilence(false)
    }
  }

  const updateSilenceRange = async (index, field, value) => {
    const newRanges = [...silenceSettings.ranges]
    newRanges[index] = { ...newRanges[index], [field]: value }
    await updateSilenceSettings({ ...silenceSettings, ranges: newRanges })
  }

  const deleteAlias = async (aliasId) => {
    try {
      await fetch(`${API_BASE_URL}/api/memory/aliases/${aliasId}?user_id=default_user`, { method: 'DELETE' })
      toast.success('Alias supprimé')
      loadMemory()
    } catch (error) {
      console.error('Erreur suppression alias:', error)
      toast.error('Erreur lors de la suppression')
    }
  }

  const connectGmail = async () => {
    setLoading(true)
    window.location.href = `${API_BASE_URL}/api/auth/gmail/start`
  }

  const connectMicrosoft = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE_URL}/api/auth/microsoft/start`)
      const data = await res.json()
      window.location.href = data.auth_url
    } catch (error) {
      console.error('Erreur Microsoft:', error)
      toast.error('Erreur lors de la connexion Microsoft')
      setLoading(false)
    }
  }

  const deleteAccount = async (accountId) => {
    if (!confirm('Supprimer ce compte ?')) return

    try {
      await fetch(`${API_BASE_URL}/api/accounts/${accountId}`, { method: 'DELETE' })
      toast.success('Compte supprimé')
      loadAccounts()
    } catch (error) {
      console.error('Erreur suppression compte:', error)
      toast.error('Erreur lors de la suppression')
    }
  }

  const createSignature = async () => {
    if (!newSignature.name || !newSignature.content || !newSignature.account_id) {
      toast.error('Veuillez remplir tous les champs')
      return
    }

    try {
      await fetch(`${API_BASE_URL}/api/signatures`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_id: newSignature.account_id,
          name: newSignature.name,
          content: newSignature.content,
          is_default: newSignature.is_default
        })
      })
      toast.success('Signature créée')
      setSignatureDialogOpen(false)
      setNewSignature({ name: '', content: '', account_id: '', is_default: false })
      loadSignatures()
    } catch (error) {
      console.error('Erreur création signature:', error)
      toast.error('Erreur lors de la création')
    }
  }

  const deleteSignature = async (signatureId) => {
    if (!confirm('Supprimer cette signature ?')) return

    try {
      await fetch(`${API_BASE_URL}/api/signatures/${signatureId}`, { method: 'DELETE' })
      toast.success('Signature supprimée')
      loadSignatures()
    } catch (error) {
      console.error('Erreur suppression signature:', error)
      toast.error('Erreur lors de la suppression')
    }
  }

  const updateSignatureDefault = async (signatureId, accountId, isDefault) => {
    try {
      const signature = signatures.find(s => s.signature_id === signatureId)
      await fetch(`${API_BASE_URL}/api/signatures/${signatureId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_id: accountId,
          name: signature.name,
          content: signature.content,
          is_default: isDefault
        })
      })
      toast.success(isDefault ? 'Signature définie par défaut' : 'Signature mise à jour')
      loadSignatures()
    } catch (error) {
      console.error('Erreur mise à jour signature:', error)
      toast.error('Erreur lors de la mise à jour')
    }
  }

  return (
    <div className="flex h-screen bg-background">
      <DesktopSidebar accounts={accounts} />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Paramètres" subtitle="Configure ton Inbox Copilot" className="text-[#2F2F2F]" />

        <div className={cn(
          "flex-1 overflow-auto",
          isMobile && "pb-20"
        )}>
          <div className="p-4 md:p-8 space-y-6 max-w-5xl mx-auto">
            
            {/* Comptes Email */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="shadow-sm border border-gray-200 bg-white">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Mail className="w-5 h-5 text-gray-800" />
                    Comptes Email Connectés
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {gmailConnected && accounts.find(acc => acc.provider === 'gmail') ? (
                    <div className="flex items-center gap-3 text-[#2F2F2F]">
                      <span className="font-semibold">Gmail connecté :</span>
                      <span className="text-[#6B7280]">{accounts.find(acc => acc.provider === 'gmail')?.email}</span>
                      <Badge className="bg-indigo-600 text-white border-0 hover:bg-indigo-700">
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        Connecté
                      </Badge>
                    </div>
                  ) : null}
                  {accounts.length === 0 ? (
                    <div className="text-center py-8">
                      <p className="text-muted-foreground mb-4">
                        Aucun compte connecté. Connectez-en un pour commencer !
                      </p>
                    </div>
                  ) : (
                    <div className="grid gap-3">
                      {accounts.map(account => (
                        <Card key={account.account_id} className="bg-white border border-gray-200 shadow-sm">
                          <CardContent className="p-4">
                            <div className="flex items-center gap-3">
                              <Avatar className="w-10 h-10">
                                <AvatarFallback className="bg-gray-200 text-gray-800">
                                  {account.email?.[0]?.toUpperCase() || 'U'}
                                </AvatarFallback>
                              </Avatar>
                              <div className="flex-1 min-w-0">
                                <p className="font-medium truncate text-gray-800">{account.name}</p>
                                <p className="text-sm text-[#6B7280] truncate">{account.email}</p>
                              </div>
                              <Badge
                                variant="outline"
                                className="bg-[#F3F4F6] text-[#2F2F2F] border-[#E5E7EB] flex-shrink-0"
                              >
                                {account.provider || account.type}
                              </Badge>
                              <Button variant="ghost" size="icon" onClick={() => deleteAccount(account.account_id)} className="flex-shrink-0">
                                <Trash2 className="w-4 h-4 text-destructive" />
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}

                  <div className="grid gap-2 md:grid-cols-2">
                    <Button onClick={connectGmail} disabled={loading} variant="outline" size="lg" className="w-full">
                      {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
                      Connecter Gmail
                    </Button>
                    <Button onClick={connectMicrosoft} disabled={loading} variant="outline" size="lg" className="w-full">
                      {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
                      Connecter Outlook
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Signatures */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card className="shadow-sm border border-gray-200 bg-white">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Signatures</CardTitle>
                    <Dialog open={signatureDialogOpen} onOpenChange={setSignatureDialogOpen}>
                      <DialogTrigger asChild>
                        <Button size="sm">
                          <Plus className="w-4 h-4 mr-2" />
                          Ajouter
                        </Button>
                      </DialogTrigger>
                      <DialogContent className={cn(isMobile && "max-w-[95%] rounded-lg")}>
                        <DialogHeader>
                          <DialogTitle>Nouvelle Signature</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                          <div>
                            <Label>Compte</Label>
                            <Select value={newSignature.account_id} onValueChange={(v) => setNewSignature({...newSignature, account_id: v})}>
                              <SelectTrigger>
                                <SelectValue placeholder="Choisir un compte" />
                              </SelectTrigger>
                              <SelectContent>
                                {accounts.map(acc => (
                                  <SelectItem key={acc.account_id} value={acc.account_id}>
                                    {acc.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label>Nom de la signature</Label>
                            <Input
                              value={newSignature.name}
                              onChange={(e) => setNewSignature({...newSignature, name: e.target.value})}
                              placeholder="Ex: Signature pro"
                            />
                          </div>
                          <div>
                            <Label>Contenu</Label>
                            <Textarea
                              value={newSignature.content}
                              onChange={(e) => setNewSignature({...newSignature, content: e.target.value})}
                              rows={6}
                              placeholder="Cordialement,\nVotre nom\nVotre titre"
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={newSignature.is_default}
                              onCheckedChange={(checked) => setNewSignature({...newSignature, is_default: checked})}
                            />
                            <Label>Définir comme signature par défaut</Label>
                          </div>
                          <Button onClick={createSignature} className="w-full" size="lg">
                            Créer la signature
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {signatures.length === 0 ? (
                    <p className="text-muted-foreground text-center py-8">
                      <span className="text-[#6B7280]">Aucune signature créée</span>
                    </p>
                  ) : (
                    <div className="space-y-4">
                      {accounts.map(account => {
                        const accountSignatures = signatures.filter(s => s.account_id === account.account_id)
                        if (accountSignatures.length === 0) return null

                        return (
                          <div key={account.account_id} className="space-y-2">
                            <h3 className="font-medium text-sm text-muted-foreground">{account.name}</h3>
                            <div className="space-y-2">
                              {accountSignatures.map(sig => (
                                <Card key={sig.signature_id} className="bg-card/50">
                                  <CardContent className="p-4">
                                    <div className="flex items-center justify-between mb-2">
                                      <div className="flex items-center gap-2">
                                        <p className="font-medium">{sig.name}</p>
                                        {sig.is_default && (
                                          <Badge variant="default" className="text-xs">
                                            <CheckCircle2 className="w-3 h-3 mr-1" />
                                            Par défaut
                                          </Badge>
                                        )}
                                      </div>
                                      <div className="flex items-center gap-2">
                                        <Switch
                                          checked={sig.is_default}
                                          onCheckedChange={(checked) => updateSignatureDefault(sig.signature_id, sig.account_id, checked)}
                                        />
                                        <Button variant="ghost" size="icon" onClick={() => deleteSignature(sig.signature_id)}>
                                          <Trash2 className="w-4 h-4 text-destructive" />
                                        </Button>
                                      </div>
                                    </div>
                                    <pre className="text-sm text-muted-foreground whitespace-pre-wrap bg-muted/30 p-3 rounded-lg">
                                      {sig.content}
                                    </pre>
                                  </CardContent>
                                </Card>
                              ))}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Mode Silence */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card className="shadow-sm border border-gray-200 bg-white overflow-hidden">
                <CardHeader className={cn(
                  "transition-colors",
                  silenceSettings.enabled && "bg-gradient-to-r from-indigo-500 to-purple-600 text-white"
                )}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "p-2 rounded-lg",
                        silenceSettings.enabled ? "bg-white/20" : "bg-indigo-100"
                      )}>
                        <BellOff className={cn("w-5 h-5", silenceSettings.enabled ? "text-white" : "text-indigo-600")} />
                      </div>
                      <div>
                        <CardTitle className={cn(silenceSettings.enabled && "text-white")}>
                          Mode Silence
                        </CardTitle>
                        <CardDescription className={cn(silenceSettings.enabled ? "text-white/80" : "text-muted-foreground")}>
                          Désactive les notifications pendant certaines heures
                        </CardDescription>
                      </div>
                    </div>
                    <Switch
                      checked={silenceSettings.enabled}
                      onCheckedChange={(enabled) => updateSilenceSettings({ ...silenceSettings, enabled })}
                      disabled={loadingSilence}
                      className={cn(silenceSettings.enabled && "data-[state=checked]:bg-white/30")}
                    />
                  </div>
                </CardHeader>
                {silenceSettings.enabled && (
                  <CardContent className="p-4 space-y-4">
                    <p className="text-sm text-muted-foreground">
                      Les notifications seront désactivées pendant ces plages horaires :
                    </p>
                    {silenceSettings.ranges?.map((range, index) => (
                      <div key={index} className="flex items-center gap-3 p-3 bg-indigo-50 dark:bg-indigo-950/20 rounded-xl">
                        <Clock className="w-4 h-4 text-indigo-600" />
                        <div className="flex items-center gap-2 flex-1">
                          <div className="flex items-center gap-2">
                            <Label className="text-sm text-muted-foreground">De</Label>
                            <Input
                              type="time"
                              value={range.start}
                              onChange={(e) => updateSilenceRange(index, 'start', e.target.value)}
                              className="w-28"
                              disabled={loadingSilence}
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <Label className="text-sm text-muted-foreground">à</Label>
                            <Input
                              type="time"
                              value={range.end}
                              onChange={(e) => updateSilenceRange(index, 'end', e.target.value)}
                              className="w-28"
                              disabled={loadingSilence}
                            />
                          </div>
                        </div>
                        {index === 0 && (
                          <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                            Pause déjeuner
                          </Badge>
                        )}
                        {index === 1 && (
                          <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                            Soirée
                          </Badge>
                        )}
                      </div>
                    ))}
                  </CardContent>
                )}
              </Card>
            </motion.div>

            {/* Comportement */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card className="shadow-sm border border-gray-200 bg-white">
                <CardHeader>
                  <CardTitle>Comportement de l'Assistant</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-start gap-3">
                    <Switch defaultChecked />
                    <div className="flex-1">
                      <p className="font-medium">Confirmation avant envoi</p>
                      <p className="text-sm text-[#6B7280]">Toujours demander confirmation avant d'envoyer un email</p>
                    </div>
                  </div>
                  <Separator />
                  <div className="flex items-start gap-3">
                    <Switch defaultChecked />
                    <div className="flex-1">
                      <p className="font-medium">Création automatique de fichiers attendus</p>
                      <p className="text-sm text-[#6B7280]">L'IA peut proposer de créer des fichiers attendus automatiquement</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Mémoire IA */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card className="shadow-sm border border-gray-200 bg-white">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      🧠 Mémoire de l'Assistant
                    </CardTitle>
                    <div className="flex gap-2">
                      <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200">
                        {memoryStats.contacts} contacts
                      </Badge>
                      <Badge variant="outline" className="bg-violet-50 text-violet-700 border-violet-200">
                        {memoryStats.aliases} alias
                      </Badge>
                      <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                        {memoryStats.vendors} fournisseurs
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  {loadingMemory ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                    </div>
                  ) : (
                    <>
                      {/* Aliases */}
                      <div>
                        <h3 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2">
                          <span>📌</span> Alias (raccourcis)
                        </h3>
                        {aliases.length === 0 ? (
                          <p className="text-sm text-gray-500 italic">Aucun alias enregistré. L'IA en créera automatiquement.</p>
                        ) : (
                          <div className="space-y-2">
                            {aliases.map(alias => (
                              <div key={alias.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                                <div className="flex items-center gap-3">
                                  <span className="font-medium text-indigo-700">"{alias.key}"</span>
                                  <span className="text-gray-400">→</span>
                                  <span className="text-gray-600 text-sm">{alias.value}</span>
                                  {alias.auto_created && (
                                    <Badge variant="outline" className="text-xs bg-gray-100 text-gray-500">auto</Badge>
                                  )}
                                  {alias.confidence < 1 && (
                                    <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700">
                                      {Math.round(alias.confidence * 100)}%
                                    </Badge>
                                  )}
                                </div>
                                <Button variant="ghost" size="icon" onClick={() => deleteAlias(alias.id)}>
                                  <Trash2 className="w-4 h-4 text-gray-400 hover:text-destructive" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      <Separator />

                      {/* Vendors */}
                      <div>
                        <h3 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2">
                          <span>🏢</span> Fournisseurs reconnus
                        </h3>
                        {vendors.length === 0 ? (
                          <p className="text-sm text-gray-500 italic">Aucun fournisseur détecté. L'IA apprendra au fil des factures.</p>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {vendors.map(vendor => (
                              <Badge key={vendor.id} variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 py-1 px-3">
                                {vendor.name}
                                {vendor.domains?.length > 0 && (
                                  <span className="text-purple-400 ml-1">@{vendor.domains[0]}</span>
                                )}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </div>

      <MobileNav />
    </div>
  )
}

export default function ParametresPage() {
  return (
    <Suspense fallback={
      <div className="flex h-screen bg-background items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    }>
      <ParametresContent />
    </Suspense>
  )
}
