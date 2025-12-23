'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Brain,
  Users,
  Building2,
  Tag,
  Star,
  Plus,
  Trash2,
  Search,
  RefreshCw,
  Loader2
} from 'lucide-react'
import Header from '@/components/Header'
import DesktopSidebar from '@/components/DesktopSidebar'
import MobileNav from '@/components/MobileNav'
import NotificationCenter from '@/components/NotificationCenter'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function MemoirePage() {
  const [vips, setVips] = useState([])
  const [aliases, setAliases] = useState([])
  const [vendors, setVendors] = useState([])
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')

  // Dialog states
  const [vipDialogOpen, setVipDialogOpen] = useState(false)
  const [aliasDialogOpen, setAliasDialogOpen] = useState(false)
  const [vendorDialogOpen, setVendorDialogOpen] = useState(false)

  // Form states
  const [newVipLabel, setNewVipLabel] = useState('')
  const [newVipEmail, setNewVipEmail] = useState('')
  const [newAliasKey, setNewAliasKey] = useState('')
  const [newAliasEmail, setNewAliasEmail] = useState('')
  const [newVendorName, setNewVendorName] = useState('')
  const [newVendorDomain, setNewVendorDomain] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [vipRes, aliasRes, vendorRes, contactRes] = await Promise.all([
        fetch(`${API_BASE}/api/memory/vips`),
        fetch(`${API_BASE}/api/memory/aliases`),
        fetch(`${API_BASE}/api/memory/vendors`),
        fetch(`${API_BASE}/api/memory/contacts`)
      ])

      if (vipRes.ok) {
        const data = await vipRes.json()
        setVips(data.vips || [])
      }
      if (aliasRes.ok) {
        const data = await aliasRes.json()
        setAliases(data.aliases || [])
      }
      if (vendorRes.ok) {
        const data = await vendorRes.json()
        setVendors(data.vendors || [])
      }
      if (contactRes.ok) {
        const data = await contactRes.json()
        setContacts(data.contacts || [])
      }
    } catch (error) {
      console.error('Error fetching memory data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // VIP CRUD
  const createVip = async () => {
    if (!newVipLabel || !newVipEmail) {
      toast.error('Remplissez tous les champs')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/memory/vips`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: newVipLabel, email: newVipEmail })
      })
      if (res.ok) {
        toast.success('VIP ajouté')
        setNewVipLabel('')
        setNewVipEmail('')
        setVipDialogOpen(false)
        fetchData()
      }
    } catch (error) {
      toast.error('Erreur')
    } finally {
      setSubmitting(false)
    }
  }

  const deleteVip = async (vipId) => {
    try {
      await fetch(`${API_BASE}/api/memory/vips/${vipId}`, { method: 'DELETE' })
      toast.success('VIP supprimé')
      setVips(prev => prev.filter(v => v.id !== vipId))
    } catch (error) {
      toast.error('Erreur')
    }
  }

  // Alias CRUD
  const createAlias = async () => {
    if (!newAliasKey || !newAliasEmail) {
      toast.error('Remplissez tous les champs')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/memory/aliases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: newAliasKey.toLowerCase(), value: newAliasEmail.toLowerCase() })
      })
      if (res.ok) {
        toast.success('Alias créé')
        setNewAliasKey('')
        setNewAliasEmail('')
        setAliasDialogOpen(false)
        fetchData()
      }
    } catch (error) {
      toast.error('Erreur')
    } finally {
      setSubmitting(false)
    }
  }

  const deleteAlias = async (aliasId) => {
    try {
      await fetch(`${API_BASE}/api/memory/aliases/${aliasId}`, { method: 'DELETE' })
      toast.success('Alias supprimé')
      setAliases(prev => prev.filter(a => a.id !== aliasId))
    } catch (error) {
      toast.error('Erreur')
    }
  }

  // Vendor CRUD
  const createVendor = async () => {
    if (!newVendorName) {
      toast.error('Nom requis')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/memory/vendors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newVendorName, domain: newVendorDomain || undefined })
      })
      if (res.ok) {
        toast.success('Fournisseur ajouté')
        setNewVendorName('')
        setNewVendorDomain('')
        setVendorDialogOpen(false)
        fetchData()
      }
    } catch (error) {
      toast.error('Erreur')
    } finally {
      setSubmitting(false)
    }
  }

  const deleteVendor = async (vendorId) => {
    try {
      await fetch(`${API_BASE}/api/memory/vendors/${vendorId}`, { method: 'DELETE' })
      toast.success('Fournisseur supprimé')
      setVendors(prev => prev.filter(v => v.id !== vendorId))
    } catch (error) {
      toast.error('Erreur')
    }
  }

  const deleteContact = async (contactId) => {
    try {
      await fetch(`${API_BASE}/api/memory/contacts/${contactId}`, { method: 'DELETE' })
      toast.success('Contact supprimé')
      setContacts(prev => prev.filter(c => c.id !== contactId))
    } catch (error) {
      toast.error('Erreur')
    }
  }

  const filterItems = (items, term) => {
    if (!term) return items
    const lower = term.toLowerCase()
    return items.filter(item => JSON.stringify(item).toLowerCase().includes(lower))
  }

  const filteredVips = filterItems(vips, searchTerm)
  const filteredAliases = filterItems(aliases, searchTerm)
  const filteredVendors = filterItems(vendors, searchTerm)
  const filteredContacts = filterItems(contacts, searchTerm)

  const ItemCard = ({ children, onDelete }) => (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-between p-3 bg-white dark:bg-card rounded-xl shadow-sm border border-border/50 hover:shadow-md transition-shadow"
    >
      {children}
      <Button variant="ghost" size="icon" onClick={onDelete} className="text-muted-foreground hover:text-destructive">
        <Trash2 className="w-4 h-4" />
      </Button>
    </motion.div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-background dark:via-background dark:to-background">
      <div className="flex h-screen">
        <DesktopSidebar />

        <div className="flex-1 flex flex-col overflow-hidden">
          <Header
            title="Mémoire"
            subtitle="VIPs, alias, fournisseurs, contacts"
            rightContent={
              <div className="flex items-center gap-2">
                <Button variant="outline" size="icon" onClick={fetchData} disabled={loading}>
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </Button>
                <NotificationCenter />
              </div>
            }
          />

          <div className="flex-1 overflow-y-auto pb-24 md:pb-6">
            <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-6">
              {/* Stats Cards */}
              <div className="grid grid-cols-4 gap-3">
                <div className="p-3 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl text-white">
                  <Star className="w-5 h-5 mb-1" />
                  <div className="text-2xl font-bold">{vips.length}</div>
                  <div className="text-xs opacity-80">VIPs</div>
                </div>
                <div className="p-3 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl text-white">
                  <Tag className="w-5 h-5 mb-1" />
                  <div className="text-2xl font-bold">{aliases.length}</div>
                  <div className="text-xs opacity-80">Alias</div>
                </div>
                <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl text-white">
                  <Building2 className="w-5 h-5 mb-1" />
                  <div className="text-2xl font-bold">{vendors.length}</div>
                  <div className="text-xs opacity-80">Fournisseurs</div>
                </div>
                <div className="p-3 bg-gradient-to-br from-green-500 to-emerald-500 rounded-xl text-white">
                  <Users className="w-5 h-5 mb-1" />
                  <div className="text-2xl font-bold">{contacts.length}</div>
                  <div className="text-xs opacity-80">Contacts</div>
                </div>
              </div>

              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Rechercher..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 bg-white dark:bg-card"
                />
              </div>

              {/* Tabs */}
              <Tabs defaultValue="vips" className="space-y-4">
                <TabsList className="grid w-full grid-cols-4 h-12">
                  <TabsTrigger value="vips" className="gap-1.5 data-[state=active]:bg-gradient-to-r data-[state=active]:from-amber-500 data-[state=active]:to-orange-500 data-[state=active]:text-white">
                    <Star className="w-4 h-4" />
                    <span className="hidden sm:inline">VIPs</span>
                  </TabsTrigger>
                  <TabsTrigger value="aliases" className="gap-1.5">
                    <Tag className="w-4 h-4" />
                    <span className="hidden sm:inline">Alias</span>
                  </TabsTrigger>
                  <TabsTrigger value="vendors" className="gap-1.5">
                    <Building2 className="w-4 h-4" />
                    <span className="hidden sm:inline">Fournisseurs</span>
                  </TabsTrigger>
                  <TabsTrigger value="contacts" className="gap-1.5">
                    <Users className="w-4 h-4" />
                    <span className="hidden sm:inline">Contacts</span>
                  </TabsTrigger>
                </TabsList>

                {/* VIPs Tab */}
                <TabsContent value="vips">
                  <Card className="border-none shadow-lg">
                    <CardHeader className="flex flex-row items-center justify-between pb-3">
                      <div>
                        <CardTitle className="flex items-center gap-2 text-amber-600">
                          <Star className="w-5 h-5" />
                          Contacts VIP
                        </CardTitle>
                        <CardDescription>
                          Priorité maximale sur leurs emails
                        </CardDescription>
                      </div>
                      <Button onClick={() => setVipDialogOpen(true)} className="gap-2 bg-gradient-to-r from-amber-500 to-orange-500">
                        <Plus className="w-4 h-4" /> Ajouter
                      </Button>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {filteredVips.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          <Star className="w-8 h-8 mx-auto mb-2 opacity-30" />
                          Aucun VIP. Ajoutez vos contacts importants.
                        </div>
                      ) : (
                        filteredVips.map((vip) => (
                          <ItemCard key={vip.id} onDelete={() => deleteVip(vip.id)}>
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center text-white font-bold">
                                {(vip.label || 'V')[0].toUpperCase()}
                              </div>
                              <div>
                                <p className="font-semibold">{vip.label}</p>
                                <p className="text-sm text-muted-foreground">{vip.email}</p>
                              </div>
                            </div>
                          </ItemCard>
                        ))
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Aliases Tab */}
                <TabsContent value="aliases">
                  <Card className="border-none shadow-lg">
                    <CardHeader className="flex flex-row items-center justify-between pb-3">
                      <div>
                        <CardTitle className="flex items-center gap-2 text-blue-600">
                          <Tag className="w-5 h-5" />
                          Alias / Raccourcis
                        </CardTitle>
                        <CardDescription>
                          "comptable" → email@exemple.com
                        </CardDescription>
                      </div>
                      <Button onClick={() => setAliasDialogOpen(true)} variant="outline" className="gap-2">
                        <Plus className="w-4 h-4" /> Ajouter
                      </Button>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {filteredAliases.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          Aucun alias
                        </div>
                      ) : (
                        filteredAliases.map((alias) => (
                          <ItemCard key={alias.id} onDelete={() => deleteAlias(alias.id)}>
                            <div>
                              <p className="font-semibold">{alias.key}</p>
                              <p className="text-sm text-muted-foreground">→ {alias.value || alias.email}</p>
                            </div>
                          </ItemCard>
                        ))
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Vendors Tab */}
                <TabsContent value="vendors">
                  <Card className="border-none shadow-lg">
                    <CardHeader className="flex flex-row items-center justify-between pb-3">
                      <div>
                        <CardTitle className="flex items-center gap-2 text-purple-600">
                          <Building2 className="w-5 h-5" />
                          Fournisseurs
                        </CardTitle>
                        <CardDescription>
                          Fournisseurs reconnus
                        </CardDescription>
                      </div>
                      <Button onClick={() => setVendorDialogOpen(true)} variant="outline" className="gap-2">
                        <Plus className="w-4 h-4" /> Ajouter
                      </Button>
                    </CardHeader>
                    <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {filteredVendors.length === 0 ? (
                        <div className="col-span-full text-center py-8 text-muted-foreground">
                          Aucun fournisseur
                        </div>
                      ) : (
                        filteredVendors.map((vendor) => (
                          <ItemCard key={vendor.id} onDelete={() => deleteVendor(vendor.id)}>
                            <div>
                              <p className="font-semibold">{vendor.name}</p>
                              {vendor.domains?.[0] && (
                                <p className="text-xs text-muted-foreground">@{vendor.domains[0]}</p>
                              )}
                            </div>
                          </ItemCard>
                        ))
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Contacts Tab */}
                <TabsContent value="contacts">
                  <Card className="border-none shadow-lg">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-green-600">
                        <Users className="w-5 h-5" />
                        Contacts appris
                      </CardTitle>
                      <CardDescription>
                        Contacts détectés depuis vos emails
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {filteredContacts.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          Aucun contact
                        </div>
                      ) : (
                        filteredContacts.map((contact) => (
                          <ItemCard key={contact.id} onDelete={() => deleteContact(contact.id)}>
                            <div>
                              <p className="font-semibold">{contact.name || contact.email?.split('@')[0]}</p>
                              <p className="text-sm text-muted-foreground">{contact.email}</p>
                            </div>
                          </ItemCard>
                        ))
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </div>
      </div>

      {/* VIP Dialog */}
      <Dialog open={vipDialogOpen} onOpenChange={setVipDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Star className="w-5 h-5 text-amber-500" />
              Nouveau VIP
            </DialogTitle>
            <DialogDescription>
              Les emails de ce contact seront prioritaires
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>Nom</Label>
              <Input value={newVipLabel} onChange={(e) => setNewVipLabel(e.target.value)} placeholder="Ma comptable, Mon avocat..." className="mt-1" />
            </div>
            <div>
              <Label>Email</Label>
              <Input type="email" value={newVipEmail} onChange={(e) => setNewVipEmail(e.target.value)} placeholder="email@exemple.com" className="mt-1" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVipDialogOpen(false)}>Annuler</Button>
            <Button onClick={createVip} disabled={submitting} className="gap-2 bg-gradient-to-r from-amber-500 to-orange-500">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Star className="w-4 h-4" />}
              Ajouter VIP
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Alias Dialog */}
      <Dialog open={aliasDialogOpen} onOpenChange={setAliasDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouvel alias</DialogTitle>
            <DialogDescription>Ex: "comptable" → "celine@cabinet.fr"</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>Raccourci</Label>
              <Input value={newAliasKey} onChange={(e) => setNewAliasKey(e.target.value)} placeholder="comptable, metro..." className="mt-1" />
            </div>
            <div>
              <Label>Email</Label>
              <Input type="email" value={newAliasEmail} onChange={(e) => setNewAliasEmail(e.target.value)} placeholder="email@exemple.com" className="mt-1" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAliasDialogOpen(false)}>Annuler</Button>
            <Button onClick={createAlias} disabled={submitting}>
              {submitting && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              Créer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Vendor Dialog */}
      <Dialog open={vendorDialogOpen} onOpenChange={setVendorDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouveau fournisseur</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>Nom</Label>
              <Input value={newVendorName} onChange={(e) => setNewVendorName(e.target.value)} placeholder="Metro, EDF..." className="mt-1" />
            </div>
            <div>
              <Label>Domaine (optionnel)</Label>
              <Input value={newVendorDomain} onChange={(e) => setNewVendorDomain(e.target.value)} placeholder="metro.fr" className="mt-1" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVendorDialogOpen(false)}>Annuler</Button>
            <Button onClick={createVendor} disabled={submitting}>
              {submitting && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              Créer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <MobileNav />
    </div>
  )
}
