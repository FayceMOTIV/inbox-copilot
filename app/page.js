'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Loader2, Copy, X, ExternalLink, Sparkles, Mail, Search, Zap, ChevronDown, Plus, MessageSquare, Trash2, Download, Paperclip, Reply, Volume2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import DesktopSidebar from '@/components/DesktopSidebar'
import MobileNav from '@/components/MobileNav'
import Header from '@/components/Header'
import Logo from '@/components/Logo'
import MotivationalMessage from '@/components/MotivationalMessage'
import EmailPanel from '@/components/EmailPanel'
import NotificationCenter from '@/components/NotificationCenter'
import { VoiceInputButton, TTSToggleButton, useTTS } from '@/components/VoiceInput'
import { AssistantResponse, AssistantResultList, AssistantActionSuggestions } from '@/components/AssistantCards'
import { useMediaQuery } from '@/hooks/use-mobile'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

const defaultSuggestions = [
  { icon: Mail, text: "Écris un mail à ma comptable", color: "from-blue-500 to-cyan-500", emoji: "✉️" },
  { icon: Search, text: "Trouve mes factures récentes", color: "from-purple-500 to-pink-500", emoji: "📄" },
  { icon: Zap, text: "Montre-moi mes emails urgents", color: "from-orange-500 to-red-500", emoji: "🔥" },
]

// EmptyState component - defined outside to prevent re-renders
const EmptyState = () => (
  <div className="text-center py-8 px-4">
    <div className="mb-4">
      <Logo size="lg" animated={false} />
    </div>
    <h2 className="text-2xl md:text-3xl font-black mb-3 text-foreground">
      Salut ! Je suis ton Copilot 🚀
    </h2>
    <MotivationalMessage />
  </div>
)

export default function AssistantPage() {
  const [mode, setMode] = useState('actions')
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [sidebarContent, setSidebarContent] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [emailDraft, setEmailDraft] = useState(null)
  const [searchResults, setSearchResults] = useState(null)
  const [conversationId, setConversationId] = useState(null)
  const [conversations, setConversations] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const [activeEmail, setActiveEmail] = useState(null)
  const [activeAttachments, setActiveAttachments] = useState([])
  const [multiEmailMode, setMultiEmailMode] = useState(false)
  const [emailsWithAttachments, setEmailsWithAttachments] = useState([])
  const [activeAccountId, setActiveAccountId] = useState(null)
  const [showEmailPanel, setShowEmailPanel] = useState(false)
  const [todaySummary, setTodaySummary] = useState(null)
  const [suggestions, setSuggestions] = useState(defaultSuggestions)
  const [ttsEnabled, setTtsEnabled] = useState(false)
  const messagesEndRef = useRef(null)
  const isMobile = useMediaQuery('(max-width: 768px)')
  const { speak, isSupported: ttsSupported } = useTTS()

  // Handle notification click to open email
  const handleNotificationEmail = (email) => {
    setActiveEmail(email)
    setActiveAccountId(email.account_id)
    setShowEmailPanel(true)
  }

  useEffect(() => {
    loadAccounts()
    loadConversations()
    loadActiveConversation()
    loadTodaySummary()
  }, [])

  const loadTodaySummary = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/today`)
      if (res.ok) {
        const data = await res.json()
        setTodaySummary(data)
        buildDynamicSuggestions(data)
      }
    } catch (error) {
      console.error('Error loading today summary:', error)
    }
  }

  const buildDynamicSuggestions = (data) => {
    const dynamicSuggestions = []

    // Add urgent email suggestion if any
    if (data?.urgent?.length > 0) {
      const urgent = data.urgent[0]
      dynamicSuggestions.push({
        icon: Zap,
        text: `Voir l'email urgent de ${urgent.from?.split('<')[0]?.trim() || 'inconnu'}`,
        color: "from-red-500 to-orange-500",
        emoji: "🔥"
      })
    }

    // Add waiting thread suggestion if any overdue
    if (data?.waiting?.some(w => w.is_overdue)) {
      dynamicSuggestions.push({
        icon: Mail,
        text: "Relancer les conversations en retard",
        color: "from-amber-500 to-yellow-500",
        emoji: "⏰"
      })
    }

    // Add document suggestion if any detected
    if (data?.documents?.length > 0) {
      dynamicSuggestions.push({
        icon: Search,
        text: `Traiter le ${data.documents[0].type} reçu`,
        color: "from-purple-500 to-pink-500",
        emoji: "📄"
      })
    }

    // Fill with defaults if needed
    const combined = [...dynamicSuggestions, ...defaultSuggestions].slice(0, 3)
    setSuggestions(combined)
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle voice transcript from VoiceInputButton
  const handleVoiceTranscript = (transcript) => {
    setMessage(transcript)
  }

  const loadAccounts = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/accounts`)
      const data = await res.json()
      setAccounts(data.accounts || [])
    } catch (error) {
      console.error('Erreur chargement comptes:', error)
    }
  }

  const loadConversations = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/conversations?user_id=default_user&limit=20`)
      const data = await res.json()
      setConversations(data.conversations || [])
    } catch (error) {
      console.error('Erreur chargement conversations:', error)
    }
  }

  const loadActiveConversation = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/conversations/current/active?user_id=default_user`)
      const data = await res.json()
      if (data.conversation_id) {
        setConversationId(data.conversation_id)
        setMessages(data.messages || [])
      }
    } catch (error) {
      console.error('Erreur chargement conversation active:', error)
    }
  }

  const loadConversation = async (convId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/conversations/${convId}?user_id=default_user`)
      const data = await res.json()
      setConversationId(data.conversation_id)
      setMessages(data.messages || [])
      setShowHistory(false)
    } catch (error) {
      console.error('Erreur chargement conversation:', error)
    }
  }

  const saveConversation = async (newMessages) => {
    try {
      if (conversationId) {
        // Update existing
        await fetch(`${API_BASE_URL}/api/conversations/${conversationId}?user_id=default_user`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: newMessages })
        })
      } else {
        // Create new
        const res = await fetch(`${API_BASE_URL}/api/conversations?user_id=default_user`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: newMessages })
        })
        const data = await res.json()
        setConversationId(data.conversation_id)
      }
      loadConversations()
    } catch (error) {
      console.error('Erreur sauvegarde conversation:', error)
    }
  }

  const startNewConversation = () => {
    setConversationId(null)
    setMessages([])
    setShowHistory(false)
  }

  const deleteConversation = async (convId, e) => {
    e.stopPropagation()
    try {
      await fetch(`${API_BASE_URL}/api/conversations/${convId}?user_id=default_user`, { method: 'DELETE' })
      loadConversations()
      if (convId === conversationId) {
        startNewConversation()
      }
    } catch (error) {
      console.error('Erreur suppression conversation:', error)
    }
  }

  const sendMessage = async () => {
    if (!message.trim()) return

    // Keep history BEFORE adding new message
    const historyForBackend = [...messages]
    const currentMessage = message

    const userMessage = { role: 'user', content: message }
    setMessages(prev => [...prev, userMessage])
    setMessage('')
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: currentMessage,
          mode,
          history: historyForBackend,
          active_email: activeEmail  // Send current email context
        })
      })

      const data = await res.json()

      // Build AI message with optional cards data
      const aiMessage = {
        role: 'assistant',
        content: data.reply,
        emails: data.context?.search_results || data.emails || [],
        documents: data.documents || [],
        suggestions: data.suggestions || []
      }
      const updatedMessages = [...historyForBackend, userMessage, aiMessage]
      setMessages(prev => [...prev, aiMessage])

      // TTS: Speak AI response if enabled
      if (ttsEnabled && data.reply) {
        speak(data.reply)
      }

      // Save conversation after each exchange
      await saveConversation(updatedMessages)

      // Handle different actions based on response
      if (data.action === 'show_email' && data.email) {
        setActiveEmail(data.email)
        setActiveAttachments(data.attachments || [])
        setActiveAccountId(data.account_id)
        setShowEmailPanel(true)
        setSidebarContent(null)  // Close other sidebars
      } else if (data.action === 'download_attachments') {
        // Handle multi-email or single email mode
        setActiveAccountId(data.account_id)

        if (data.multi_email && data.emails_with_attachments?.length > 0) {
          // Multi-email mode: multiple invoices/emails to download
          setMultiEmailMode(true)
          setEmailsWithAttachments(data.emails_with_attachments)
          setActiveAttachments(data.attachments || [])
          setActiveEmail(data.emails_with_attachments[0]) // First email as reference
          setShowEmailPanel(true)
          toast.info(`${data.emails_with_attachments.length} emails avec ${data.attachments?.length || 0} fichiers`, {
            description: 'Cliquez sur "Tout télécharger" pour récupérer tous les fichiers'
          })
        } else if (data.email) {
          // Single email mode
          setMultiEmailMode(false)
          setEmailsWithAttachments([])
          setActiveEmail(data.email)
          setActiveAttachments(data.attachments || [])
          setShowEmailPanel(true)
          if (data.attachments?.length > 0) {
            toast.info(`${data.attachments.length} pièce(s) jointe(s) disponible(s)`, {
              description: 'Cliquez sur "Tout télécharger" dans le panneau'
            })
          }
        }
      } else if (data.action === 'compose_reply' && activeEmail) {
        handleReplyToEmail(activeEmail)
      } else if (data.action === 'compose_email') {
        if (data.emailDraft) {
          setEmailDraft({
            ...data.emailDraft,
            accountId: data.account_id || accounts[0]?.account_id
          })
        }
        setSidebarContent('email')
      } else if (data.action === 'send_email' && data.emailDraft) {
        setEmailDraft({
          ...data.emailDraft,
          accountId: data.emailDraft.accountId || (accounts[0]?.account_id || null)
        })
        setSidebarContent('email')
      }

      // Update search results if available
      if (data.context?.search_results?.length > 0) {
        setSearchResults(data.context.search_results)
      }

    } catch (error) {
      console.error('Erreur:', error)
      toast.error("Erreur lors de la communication avec l'IA")
      setMessages(prev => [...prev, { role: 'assistant', content: "Désolé, une erreur s'est produite." }])
    } finally {
      setLoading(false)
    }
  }

  const handleReplyToEmail = (email) => {
    const replySubject = email.subject?.startsWith('Re:') ? email.subject : `Re: ${email.subject}`
    setEmailDraft({
      to: email.from_email || email.from,
      subject: replySubject,
      body: `\n\n---\nLe ${email.date}, ${email.from} a écrit :\n${email.snippet || ''}`,
      accountId: activeAccountId || accounts[0]?.account_id
    })
    setSidebarContent('email')
    setShowEmailPanel(false)
  }

  const handleDownloadComplete = (files) => {
    // Could add files to a list or notify user
    console.log('Downloaded files:', files)
  }

  const performSearch = async (searchQuery) => {
    try {
      const accountId = searchQuery.accountId || accounts[0]?.account_id
      if (!accountId) {
        toast.error('Aucun compte email connecté')
        return
      }

      const res = await fetch('http://localhost:8000/api/email/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_id: accountId,
          query_string: searchQuery.queryString
        })
      })

      const data = await res.json()
      setSearchResults(data.results || [])
      setSidebarContent('search')
    } catch (error) {
      console.error('Erreur recherche:', error)
      toast.error('Erreur lors de la recherche')
    }
  }

  const createExpectedFile = async (fileData) => {
    try {
      await fetch('http://localhost:8000/api/expected-files', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fileData)
      })
      toast.success('✅ Fichier attendu créé !')
    } catch (error) {
      console.error('Erreur création fichier attendu:', error)
      toast.error('Erreur lors de la création')
    }
  }

  const sendEmail = async () => {
    if (!emailDraft?.to || !emailDraft?.subject) {
      toast.error('Destinataire et objet requis')
      return
    }

    try {
      const res = await fetch('http://localhost:8000/api/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_id: emailDraft.accountId,
          to: emailDraft.to,
          subject: emailDraft.subject,
          body: emailDraft.body,
          signature_id: emailDraft.signatureId || null
        })
      })

      if (res.ok) {
        toast.success('✉️ Email envoyé !')
        setEmailDraft(null)
        setSidebarContent(null)
      } else {
        throw new Error('Erreur envoi')
      }
    } catch (error) {
      console.error('Erreur envoi email:', error)
      toast.error("Erreur lors de l'envoi de l'email")
    }
  }

  const modifyInChat = () => {
    if (emailDraft) {
      setMessage(`Modifie cet email :

Destinataire: ${emailDraft.to}
Objet: ${emailDraft.subject}

${emailDraft.body}`)
      setSidebarContent(null)
    }
  }

  const handleSuggestionClick = (text) => {
    setMessage(text)
  }

  const BottomSheet = () => (
    <motion.div
      initial={{ y: '100%' }}
      animate={{ y: 0 }}
      exit={{ y: '100%' }}
      transition={{ type: 'spring', damping: 30, stiffness: 300 }}
      className="fixed inset-x-0 bottom-0 z-50 bottom-sheet max-h-[85vh] overflow-hidden"
    >
      <div className="relative">
        <div className="flex justify-center pt-3 pb-2">
          <div className="w-12 h-1.5 bg-gray-300 rounded-full" />
        </div>
        
        <div className="flex items-center justify-between px-4 pb-3">
          <h3 className="text-lg font-bold text-foreground">
            {sidebarContent === 'email' ? '✉️ Brouillon' : '🔍 Résultats'}
          </h3>
          <Button variant="ghost" size="icon" onClick={() => setSidebarContent(null)} className="rounded-full">
            <X className="w-5 h-5" />
          </Button>
        </div>

        <ScrollArea className="px-4 pb-6" style={{ maxHeight: 'calc(85vh - 80px)' }}>
          {sidebarContent === 'email' && emailDraft && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-semibold mb-2 block text-foreground">Compte</label>
                <Select value={emailDraft.accountId} onValueChange={(v) => setEmailDraft({...emailDraft, accountId: v})}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choisir un compte" />
                  </SelectTrigger>
                  <SelectContent>
                    {accounts.map(acc => (
                      <SelectItem key={acc.account_id} value={acc.account_id}>
                        {acc.name} ({acc.type})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-semibold mb-2 block text-foreground">Destinataire</label>
                <Input
                  value={emailDraft.to}
                  onChange={(e) => setEmailDraft({...emailDraft, to: e.target.value})}
                  placeholder="email@example.com"
                />
              </div>

              <div>
                <label className="text-sm font-semibold mb-2 block text-foreground">Objet</label>
                <Input
                  value={emailDraft.subject}
                  onChange={(e) => setEmailDraft({...emailDraft, subject: e.target.value})}
                  placeholder="Objet de l'email"
                />
              </div>

              <div>
                <label className="text-sm font-semibold mb-2 block text-foreground">Corps</label>
                <Textarea
                  value={emailDraft.body}
                  onChange={(e) => setEmailDraft({...emailDraft, body: e.target.value})}
                  rows={10}
                  placeholder="Contenu de l'email..."
                />
              </div>

              <div className="flex gap-2 pt-2">
                <Button onClick={sendEmail} className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 h-12">
                  <Send className="w-4 h-4 mr-2" />
                  Envoyer
                </Button>
                <Button variant="outline" onClick={modifyInChat} className="h-12">
                  Modifier
                </Button>
                <Button variant="ghost" size="icon" onClick={() => {
                  navigator.clipboard.writeText(emailDraft.body)
                  toast.success('📋 Copié !')
                }} className="rounded-full h-12 w-12">
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {sidebarContent === 'search' && searchResults && (
            <div className="space-y-3">
              {searchResults.length === 0 ? (
                <p className="text-readable text-center py-8">Aucun résultat</p>
              ) : (
                searchResults.map((email, idx) => (
                  <Card
                    key={idx}
                    className="hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => {
                      setActiveEmail(email)
                      setActiveAttachments(email.attachments || [])
                      setActiveAccountId(accounts[0]?.account_id)
                      setShowEmailPanel(true)
                      setSidebarContent(null)
                    }}
                  >
                    <CardContent className="p-4">
                      <div className="text-xs text-readable-muted mb-1">{email.date}</div>
                      <div className="font-medium text-sm mb-1 text-foreground">{email.from}</div>
                      <div className="font-semibold mb-2 text-foreground">{email.subject}</div>
                      <p className="text-sm text-readable line-clamp-2">{email.snippet}</p>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}
        </ScrollArea>
      </div>
    </motion.div>
  )

  const DesktopSidebarPanel = () => (
    <div className="w-96 border-l border-border glass overflow-auto">
      <div className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-foreground">
            {sidebarContent === 'email' ? '✉️ Brouillon' : '🔍 Résultats'}
          </h3>
          <Button variant="ghost" size="icon" onClick={() => setSidebarContent(null)} className="rounded-full">
            <X className="w-5 h-5" />
          </Button>
        </div>

        {sidebarContent === 'email' && emailDraft && (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-semibold mb-2 block text-foreground">Compte</label>
              <Select value={emailDraft.accountId} onValueChange={(v) => setEmailDraft({...emailDraft, accountId: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un compte" />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map(acc => (
                    <SelectItem key={acc.account_id} value={acc.account_id}>
                      {acc.name} ({acc.type})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-semibold mb-2 block text-foreground">Destinataire</label>
              <Input
                value={emailDraft.to}
                onChange={(e) => setEmailDraft({...emailDraft, to: e.target.value})}
                placeholder="email@example.com"
              />
            </div>

            <div>
              <label className="text-sm font-semibold mb-2 block text-foreground">Objet</label>
              <Input
                value={emailDraft.subject}
                onChange={(e) => setEmailDraft({...emailDraft, subject: e.target.value})}
                placeholder="Objet de l'email"
              />
            </div>

            <div>
              <label className="text-sm font-semibold mb-2 block text-foreground">Corps</label>
              <Textarea
                value={emailDraft.body}
                onChange={(e) => setEmailDraft({...emailDraft, body: e.target.value})}
                rows={12}
                placeholder="Contenu de l'email..."
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={sendEmail} className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700">
                <Send className="w-4 h-4 mr-2" />
                Envoyer
              </Button>
              <Button variant="outline" onClick={modifyInChat}>
                Modifier
              </Button>
              <Button variant="ghost" size="icon" onClick={() => {
                navigator.clipboard.writeText(emailDraft.body)
                toast.success('📋 Copié !')
              }} className="rounded-full">
                <Copy className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}

        {sidebarContent === 'search' && searchResults && (
          <div className="space-y-3">
            {searchResults.length === 0 ? (
              <p className="text-readable text-center py-8">Aucun résultat</p>
            ) : (
              searchResults.map((email, idx) => (
                <Card
                  key={idx}
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => {
                    setActiveEmail(email)
                    setActiveAttachments(email.attachments || [])
                    setActiveAccountId(accounts[0]?.account_id)
                    setShowEmailPanel(true)
                    setSidebarContent(null)
                  }}
                >
                  <CardContent className="p-4">
                    <div className="text-xs text-readable-muted mb-1">{email.date}</div>
                    <div className="font-medium text-sm mb-1 text-foreground">{email.from}</div>
                    <div className="font-semibold mb-2 text-foreground">{email.subject}</div>
                    <p className="text-sm text-readable line-clamp-2">{email.snippet}</p>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {!isMobile && <DesktopSidebar accounts={accounts} />}

      <div className="flex-1 flex flex-col">
        {!isMobile && (
          <Header
            title="💬 Inbox Copilot"
            subtitle={<span className="text-[#111827]">Tu parles, je gère</span>}
            rightContent={
              <div className="flex items-center gap-2">
                <TTSToggleButton
                  enabled={ttsEnabled}
                  onToggle={() => setTtsEnabled(!ttsEnabled)}
                />
                <NotificationCenter onSelectEmail={handleNotificationEmail} />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={startNewConversation}
                  className="rounded-full"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Nouvelle
                </Button>
                <Button
                  variant={showHistory ? "default" : "outline"}
                  size="sm"
                  onClick={() => setShowHistory(!showHistory)}
                  className="rounded-full"
                >
                  <MessageSquare className="w-4 h-4 mr-1" />
                  Historique
                </Button>
              </div>
            }
          />
        )}

        {!isMobile && (
          <div className="px-6 py-4 glass border-b border-border">
            <div className="flex gap-2 items-center mb-3">
              <button
                onClick={() => setMode('actions')}
                className={cn(
                  "px-5 py-2.5 rounded-full text-sm font-bold transition-all",
                  mode === 'actions' 
                    ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg" 
                    : "bg-secondary/70 hover:bg-secondary text-foreground"
                )}
              >
                ⚡ Actions email
              </button>
              <button
                onClick={() => setMode('discussion')}
                className={cn(
                  "px-5 py-2.5 rounded-full text-sm font-bold transition-all",
                  mode === 'discussion' 
                    ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg" 
                    : "bg-secondary/70 hover:bg-secondary text-foreground"
                )}
              >
                💭 Discussion
              </button>
              <p className="text-xs text-readable-muted ml-2 font-medium">
                {mode === 'actions' ? 'Je peux agir sur tes emails' : 'Mode conseil uniquement'}
              </p>
            </div>
            
            {messages.length === 0 && (
              <div className="flex gap-2 overflow-x-auto hide-scrollbar pb-1">
                {suggestions.map((sug, idx) => (
                  <motion.button
                    key={idx}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.1 }}
                    whileHover={{ scale: 1.03, y: -2 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => handleSuggestionClick(sug.text)}
                    className={cn(
                      "suggestion-pill flex items-center gap-2 px-4 py-3 rounded-2xl text-sm font-semibold whitespace-nowrap shadow-md",
                      "bg-gradient-to-r text-white",
                      sug.color
                    )}
                  >
                    <span className="text-base">{sug.emoji}</span>
                    <span className="max-w-xs truncate">{sug.text}</span>
                  </motion.button>
                ))}
              </div>
            )}
          </div>
        )}

        {isMobile && (
          <div className="px-4 pt-4 pb-2 flex items-center justify-between">
            <h2 className="text-lg font-bold">Inbox Copilot</h2>
            <div className="flex gap-1">
              <TTSToggleButton
                enabled={ttsEnabled}
                onToggle={() => setTtsEnabled(!ttsEnabled)}
              />
              <NotificationCenter onSelectEmail={handleNotificationEmail} />
              <Button
                variant="outline"
                size="sm"
                onClick={startNewConversation}
                className="rounded-full h-9 w-9 p-0"
              >
                <Plus className="w-4 h-4" />
              </Button>
              <Button
                variant={showHistory ? "default" : "outline"}
                size="sm"
                onClick={() => setShowHistory(!showHistory)}
                className="rounded-full h-9 w-9 p-0"
              >
                <MessageSquare className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}

        {isMobile && messages.length === 0 && (
          <div className="px-4 pb-2 flex gap-2 overflow-x-auto hide-scrollbar">
            {suggestions.map((sug, idx) => (
              <motion.button
                key={idx}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => handleSuggestionClick(sug.text)}
                className={cn(
                  "flex items-center gap-2 px-4 py-3 rounded-2xl text-sm font-semibold whitespace-nowrap shadow-md",
                  "bg-gradient-to-r text-white",
                  sug.color
                )}
              >
                <span>{sug.emoji}</span>
                <span className="max-w-[180px] truncate">{sug.text}</span>
              </motion.button>
            ))}
          </div>
        )}

        <ScrollArea className={cn(
          "flex-1 px-4",
          isMobile ? "pb-32" : "pb-4"
        )}>
          <div className={cn(
            "py-6",
            !isMobile && "chat-card px-6 my-4"
          )}>
            {messages.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="space-y-4">
                {messages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{
                      type: "spring",
                      stiffness: 400,
                      damping: 25
                    }}
                    className={cn(
                      "flex gap-2 items-end",
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    )}
                  >
                    {msg.role === 'user' ? (
                      <div className="max-w-[85%] md:max-w-[75%] rounded-3xl px-5 py-3.5 shadow-md user-bubble rounded-br-md">
                        <p className="text-sm md:text-base leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    ) : (
                      <div className="max-w-[85%] md:max-w-[75%] rounded-3xl px-5 py-3.5 shadow-md ai-bubble rounded-bl-md">
                        <AssistantResponse
                          text={msg.content}
                          emails={msg.emails}
                          documents={msg.documents}
                          suggestions={msg.suggestions}
                          onEmailClick={(email) => {
                            setActiveEmail(email)
                            setActiveAccountId(email.account_id)
                            setShowEmailPanel(true)
                          }}
                          onDocClick={(doc) => {
                            setActiveEmail(doc)
                            setActiveAccountId(doc.account_id)
                            setShowEmailPanel(true)
                          }}
                          onSuggestionClick={(sug) => {
                            setMessage(sug.action || sug.text)
                          }}
                        />
                      </div>
                    )}
                  </motion.div>
                ))}

                {loading && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex gap-2 items-end"
                  >
                    <div className="ai-bubble rounded-bl-md rounded-3xl px-5 py-3.5 flex items-center gap-3">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                      >
                        <Sparkles className="w-5 h-5" />
                      </motion.div>
                      <span className="text-sm font-medium">Je réfléchis...</span>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </ScrollArea>

        <div className={cn(
          "glass border-t border-border p-4",
          isMobile && "fixed bottom-20 left-0 right-0 z-30"
        )}>
          <div className={cn(!isMobile && "max-w-[700px] mx-auto", "flex gap-2 items-end")}>
            <div className="flex-1 relative">
              <Input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Parle-moi... 💬"
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                disabled={loading}
                className="pr-14 h-14 text-base rounded-3xl border-2 border-primary/20 focus:border-primary/50 bg-white"
              />
              <VoiceInputButton
                onTranscript={handleVoiceTranscript}
                disabled={loading}
                className="absolute right-2 top-1/2 -translate-y-1/2"
              />
            </div>
            <Button
              onClick={sendMessage}
              disabled={loading || !message.trim()}
              size="icon"
              className="h-14 w-14 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 shadow-lg"
            >
              {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : <Send className="w-6 h-6" />}
            </Button>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {sidebarContent && (
          isMobile ? <BottomSheet /> : <DesktopSidebarPanel />
        )}
      </AnimatePresence>

      {/* History Panel */}
      <AnimatePresence>
        {showHistory && !isMobile && (
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 w-80 bg-card border-l border-border shadow-xl z-50 overflow-hidden"
          >
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="font-bold text-lg">Historique</h3>
              <Button variant="ghost" size="icon" onClick={() => setShowHistory(false)} className="rounded-full">
                <X className="w-5 h-5" />
              </Button>
            </div>
            <ScrollArea className="h-[calc(100vh-80px)]">
              <div className="p-4 space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2 rounded-xl"
                  onClick={startNewConversation}
                >
                  <Plus className="w-4 h-4" />
                  Nouvelle conversation
                </Button>

                {conversations.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    Aucune conversation
                  </p>
                ) : (
                  conversations.map((conv) => (
                    <motion.div
                      key={conv.conversation_id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={cn(
                        "p-3 rounded-xl cursor-pointer transition-colors group relative",
                        conv.conversation_id === conversationId
                          ? "bg-primary/10 border border-primary/20"
                          : "hover:bg-secondary"
                      )}
                      onClick={() => loadConversation(conv.conversation_id)}
                    >
                      <div className="pr-8">
                        <p className="font-medium text-sm truncate">{conv.title}</p>
                        <p className="text-xs text-muted-foreground truncate mt-1">
                          {conv.preview || 'Pas de messages'}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {conv.message_count || 0} messages
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 rounded-full hover:bg-destructive/10 hover:text-destructive"
                        onClick={(e) => deleteConversation(conv.conversation_id, e)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </motion.div>
                  ))
                )}
              </div>
            </ScrollArea>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile History */}
      <AnimatePresence>
        {showHistory && isMobile && (
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed inset-0 bg-background z-50"
          >
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="font-bold text-lg">Historique</h3>
              <Button variant="ghost" size="icon" onClick={() => setShowHistory(false)} className="rounded-full">
                <X className="w-5 h-5" />
              </Button>
            </div>
            <ScrollArea className="h-[calc(100vh-80px)]">
              <div className="p-4 space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2 rounded-xl"
                  onClick={startNewConversation}
                >
                  <Plus className="w-4 h-4" />
                  Nouvelle conversation
                </Button>

                {conversations.map((conv) => (
                  <motion.div
                    key={conv.conversation_id}
                    className={cn(
                      "p-3 rounded-xl cursor-pointer transition-colors group relative",
                      conv.conversation_id === conversationId
                        ? "bg-primary/10 border border-primary/20"
                        : "hover:bg-secondary"
                    )}
                    onClick={() => loadConversation(conv.conversation_id)}
                  >
                    <div className="pr-8">
                      <p className="font-medium text-sm truncate">{conv.title}</p>
                      <p className="text-xs text-muted-foreground truncate mt-1">
                        {conv.preview || 'Pas de messages'}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 rounded-full"
                      onClick={(e) => deleteConversation(conv.conversation_id, e)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </motion.div>
                ))}
              </div>
            </ScrollArea>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Email Panel */}
      <EmailPanel
        email={activeEmail}
        attachments={activeAttachments}
        accountId={activeAccountId}
        isOpen={showEmailPanel}
        onClose={() => {
          setShowEmailPanel(false)
          setMultiEmailMode(false)
          setEmailsWithAttachments([])
        }}
        onReply={handleReplyToEmail}
        onDownloadComplete={handleDownloadComplete}
        multiEmailMode={multiEmailMode}
        emailsWithAttachments={emailsWithAttachments}
      />

      {isMobile && <MobileNav />}
    </div>
  )
}
