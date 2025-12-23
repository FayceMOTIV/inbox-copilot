'use client'

import { motion } from 'framer-motion'
import {
  Mail,
  FileText,
  Star,
  AlertCircle,
  Clock,
  ChevronRight,
  Sparkles,
  Download,
  Reply,
  Check,
  ExternalLink
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

// Short text message with markdown-like formatting
export function AssistantMessageText({ content, className = '' }) {
  // Parse content into short bullets if too long
  const formatContent = (text) => {
    if (!text) return null

    // If text has newlines, split into lines
    const lines = text.split('\n').filter(l => l.trim())

    // If more than 5 lines, summarize
    if (lines.length > 5) {
      return (
        <div className="space-y-2">
          {lines.slice(0, 4).map((line, i) => (
            <p key={i} className="text-sm leading-relaxed">
              {line.startsWith('•') || line.startsWith('-') ? line : `• ${line}`}
            </p>
          ))}
          <p className="text-xs text-muted-foreground">
            +{lines.length - 4} autres éléments
          </p>
        </div>
      )
    }

    return (
      <div className="space-y-1">
        {lines.map((line, i) => (
          <p key={i} className="text-sm leading-relaxed">{line}</p>
        ))}
      </div>
    )
  }

  return (
    <div className={`prose prose-sm dark:prose-invert max-w-none ${className}`}>
      {formatContent(content)}
    </div>
  )
}

// Email result card
export function AssistantEmailCard({ email, onClick, showActions = true }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
    >
      <Card
        className={`cursor-pointer transition-all hover:shadow-md overflow-hidden ${
          email.priority === 'urgent' ? 'border-l-4 border-l-red-500' :
          email.is_vip ? 'border-l-4 border-l-amber-500' :
          'border-l-4 border-l-blue-500'
        }`}
        onClick={onClick}
      >
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className={`p-2 rounded-lg flex-shrink-0 ${
              email.priority === 'urgent' ? 'bg-red-100 dark:bg-red-950/50' :
              email.is_vip ? 'bg-amber-100 dark:bg-amber-950/50' :
              'bg-blue-100 dark:bg-blue-950/50'
            }`}>
              {email.priority === 'urgent' ? (
                <AlertCircle className="w-5 h-5 text-red-600" />
              ) : email.is_vip ? (
                <Star className="w-5 h-5 text-amber-600" />
              ) : (
                <Mail className="w-5 h-5 text-blue-600" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                {email.is_vip && (
                  <Badge className="bg-gradient-to-r from-amber-500 to-orange-500 text-white border-none text-xs">
                    VIP
                  </Badge>
                )}
                {email.priority === 'urgent' && (
                  <Badge variant="destructive" className="text-xs">Urgent</Badge>
                )}
                {email.has_attachments && (
                  <Badge variant="outline" className="text-xs">
                    <FileText className="w-3 h-3 mr-1" />PJ
                  </Badge>
                )}
              </div>
              <p className="font-semibold text-sm truncate">
                {email.from?.split('<')[0]?.trim() || email.from_email}
              </p>
              <p className="text-sm font-medium truncate mt-0.5">{email.subject}</p>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {email.snippet}
              </p>
              {email.reason && (
                <div className="flex items-center gap-1 mt-2 text-xs text-primary">
                  <Sparkles className="w-3 h-3" />
                  <span>{email.reason}</span>
                </div>
              )}
            </div>
            <ChevronRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Email result list
export function AssistantResultList({ emails, onEmailClick, title, maxItems = 5 }) {
  if (!emails || emails.length === 0) return null

  const displayEmails = emails.slice(0, maxItems)

  return (
    <div className="space-y-3">
      {title && (
        <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
          <Mail className="w-4 h-4" />
          {title} ({emails.length})
        </h4>
      )}
      <div className="space-y-2">
        {displayEmails.map((email, i) => (
          <AssistantEmailCard
            key={email.email_id || email.id || i}
            email={email}
            onClick={() => onEmailClick?.(email)}
          />
        ))}
      </div>
      {emails.length > maxItems && (
        <p className="text-xs text-muted-foreground text-center">
          +{emails.length - maxItems} autres résultats
        </p>
      )}
    </div>
  )
}

// Document card
export function AssistantDocCard({ doc, onClick }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
    >
      <Card
        className="cursor-pointer transition-all hover:shadow-md border-l-4 border-l-purple-500"
        onClick={onClick}
      >
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-950/50 flex-shrink-0">
              <FileText className="w-5 h-5 text-purple-600" />
            </div>
            <div className="flex-1 min-w-0">
              <Badge variant="outline" className="text-xs mb-1">
                {doc.doc_type || doc.type || 'Document'}
              </Badge>
              <p className="font-semibold text-sm truncate">{doc.subject}</p>
              <p className="text-xs text-muted-foreground truncate">
                De: {doc.from?.split('<')[0]?.trim()}
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Document list
export function AssistantDocList({ documents, onDocClick, title }) {
  if (!documents || documents.length === 0) return null

  return (
    <div className="space-y-3">
      {title && (
        <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
          <FileText className="w-4 h-4" />
          {title} ({documents.length})
        </h4>
      )}
      <div className="space-y-2">
        {documents.slice(0, 3).map((doc, i) => (
          <AssistantDocCard
            key={doc.email_id || i}
            doc={doc}
            onClick={() => onDocClick?.(doc)}
          />
        ))}
      </div>
    </div>
  )
}

// Action suggestions chips
export function AssistantActionSuggestions({ suggestions, onSuggestionClick }) {
  if (!suggestions || suggestions.length === 0) return null

  const getIcon = (type) => {
    switch (type) {
      case 'urgent': return <AlertCircle className="w-4 h-4" />
      case 'waiting': return <Clock className="w-4 h-4" />
      case 'document': return <FileText className="w-4 h-4" />
      case 'reply': return <Reply className="w-4 h-4" />
      case 'download': return <Download className="w-4 h-4" />
      default: return <Sparkles className="w-4 h-4" />
    }
  }

  const getColor = (type) => {
    switch (type) {
      case 'urgent': return 'from-red-500 to-rose-600'
      case 'waiting': return 'from-blue-500 to-cyan-600'
      case 'document': return 'from-purple-500 to-violet-600'
      default: return 'from-indigo-500 to-purple-600'
    }
  }

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
        <Sparkles className="w-3 h-3" />
        Actions rapides
      </h4>
      <div className="flex flex-wrap gap-2">
        {suggestions.slice(0, 4).map((suggestion, i) => (
          <motion.button
            key={i}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onSuggestionClick?.(suggestion)}
            className={`flex items-center gap-2 px-3 py-2 rounded-full text-xs font-semibold text-white shadow-md bg-gradient-to-r ${getColor(suggestion.type)}`}
          >
            {getIcon(suggestion.type)}
            <span className="max-w-[150px] truncate">{suggestion.action}</span>
          </motion.button>
        ))}
      </div>
    </div>
  )
}

// Quick actions after response
export function AssistantQuickActions({ actions, onAction }) {
  const defaultActions = [
    { id: 'more', label: 'Plus de détails', icon: ChevronRight },
    { id: 'done', label: 'Marquer traité', icon: Check },
    { id: 'open', label: 'Ouvrir Gmail', icon: ExternalLink },
  ]

  const displayActions = actions || defaultActions

  return (
    <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-border/50">
      {displayActions.slice(0, 3).map((action, i) => (
        <Button
          key={action.id || i}
          variant="outline"
          size="sm"
          className="rounded-full text-xs h-8"
          onClick={() => onAction?.(action)}
        >
          {action.icon && <action.icon className="w-3 h-3 mr-1" />}
          {action.label}
        </Button>
      ))}
    </div>
  )
}

// Wrapper for AI response with cards
export function AssistantResponse({
  text,
  emails,
  documents,
  suggestions,
  onEmailClick,
  onDocClick,
  onSuggestionClick,
  onAction
}) {
  return (
    <div className="space-y-4">
      {text && <AssistantMessageText content={text} />}
      {emails && emails.length > 0 && (
        <AssistantResultList
          emails={emails}
          onEmailClick={onEmailClick}
          title="Résultats"
        />
      )}
      {documents && documents.length > 0 && (
        <AssistantDocList
          documents={documents}
          onDocClick={onDocClick}
          title="Documents"
        />
      )}
      {suggestions && suggestions.length > 0 && (
        <AssistantActionSuggestions
          suggestions={suggestions}
          onSuggestionClick={onSuggestionClick}
        />
      )}
    </div>
  )
}
