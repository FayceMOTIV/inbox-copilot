'use client'

import { motion } from 'framer-motion'
import {
  Mail,
  Search,
  Bell,
  FileText,
  Star,
  Clock,
  CheckCircle2,
  Inbox,
  MessageSquare,
  Sparkles
} from 'lucide-react'
import { Button } from '@/components/ui/button'

// Base empty state with animation
function BaseEmptyState({
  icon: Icon,
  iconColor = 'text-gray-400',
  bgGradient = 'from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900',
  title,
  description,
  action,
  actionLabel,
  secondaryAction,
  secondaryLabel
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-12 px-4 text-center"
    >
      <motion.div
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
        className={`w-20 h-20 rounded-full bg-gradient-to-br ${bgGradient} flex items-center justify-center mb-4 shadow-lg`}
      >
        <Icon className={`w-10 h-10 ${iconColor}`} />
      </motion.div>
      <h3 className="text-lg font-bold text-foreground mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-xs mb-6">{description}</p>
      <div className="flex flex-col sm:flex-row gap-2">
        {action && (
          <Button
            onClick={action}
            className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-full px-6"
          >
            {actionLabel}
          </Button>
        )}
        {secondaryAction && (
          <Button
            variant="outline"
            onClick={secondaryAction}
            className="rounded-full px-6"
          >
            {secondaryLabel}
          </Button>
        )}
      </div>
    </motion.div>
  )
}

// No emails / inbox empty
export function EmptyInbox({ onRefresh }) {
  return (
    <BaseEmptyState
      icon={Inbox}
      iconColor="text-blue-500"
      bgGradient="from-blue-100 to-cyan-100 dark:from-blue-950/50 dark:to-cyan-950/50"
      title="Boite de reception vide"
      description="Aucun email pour le moment. Tout est sous controle !"
      action={onRefresh}
      actionLabel="Actualiser"
    />
  )
}

// No search results
export function EmptySearch({ query, onClear }) {
  return (
    <BaseEmptyState
      icon={Search}
      iconColor="text-purple-500"
      bgGradient="from-purple-100 to-pink-100 dark:from-purple-950/50 dark:to-pink-950/50"
      title="Aucun resultat"
      description={query ? `Aucun email ne correspond a "${query}"` : "Essayez une autre recherche"}
      action={onClear}
      actionLabel="Effacer la recherche"
    />
  )
}

// No notifications
export function EmptyNotifications() {
  return (
    <BaseEmptyState
      icon={Bell}
      iconColor="text-amber-500"
      bgGradient="from-amber-100 to-orange-100 dark:from-amber-950/50 dark:to-orange-950/50"
      title="Aucune notification"
      description="Vous etes a jour ! Aucune action requise."
    />
  )
}

// No documents
export function EmptyDocuments({ onSearch }) {
  return (
    <BaseEmptyState
      icon={FileText}
      iconColor="text-emerald-500"
      bgGradient="from-emerald-100 to-teal-100 dark:from-emerald-950/50 dark:to-teal-950/50"
      title="Aucun document"
      description="Aucune facture ou document detecte pour le moment."
      action={onSearch}
      actionLabel="Rechercher"
    />
  )
}

// No VIPs
export function EmptyVIPs({ onAdd }) {
  return (
    <BaseEmptyState
      icon={Star}
      iconColor="text-yellow-500"
      bgGradient="from-yellow-100 to-amber-100 dark:from-yellow-950/50 dark:to-amber-950/50"
      title="Aucun VIP"
      description="Ajoutez vos contacts importants pour ne jamais rater leurs emails."
      action={onAdd}
      actionLabel="Ajouter un VIP"
    />
  )
}

// No waiting threads
export function EmptyWaiting() {
  return (
    <BaseEmptyState
      icon={CheckCircle2}
      iconColor="text-green-500"
      bgGradient="from-green-100 to-emerald-100 dark:from-green-950/50 dark:to-emerald-950/50"
      title="Tout est a jour"
      description="Aucune conversation en attente de reponse."
    />
  )
}

// No urgent emails
export function EmptyUrgent() {
  return (
    <BaseEmptyState
      icon={Clock}
      iconColor="text-green-500"
      bgGradient="from-green-100 to-emerald-100 dark:from-green-950/50 dark:to-emerald-950/50"
      title="Aucun email urgent"
      description="Super ! Aucun email ne necessite une attention immediate."
    />
  )
}

// No conversations
export function EmptyConversations({ onStart }) {
  return (
    <BaseEmptyState
      icon={MessageSquare}
      iconColor="text-indigo-500"
      bgGradient="from-indigo-100 to-violet-100 dark:from-indigo-950/50 dark:to-violet-950/50"
      title="Aucune conversation"
      description="Commencez a discuter avec votre assistant pour gerer vos emails."
      action={onStart}
      actionLabel="Nouvelle conversation"
    />
  )
}

// No recap data
export function EmptyRecap({ onGenerate }) {
  return (
    <BaseEmptyState
      icon={Sparkles}
      iconColor="text-purple-500"
      bgGradient="from-purple-100 to-pink-100 dark:from-purple-950/50 dark:to-pink-950/50"
      title="Pas encore de recap"
      description="Generez votre premier recap pour voir un resume de vos emails."
      action={onGenerate}
      actionLabel="Generer le recap"
    />
  )
}

// Generic empty state
export function EmptyState({
  icon = Mail,
  title = "Rien a afficher",
  description = "Aucun element a afficher pour le moment.",
  action,
  actionLabel
}) {
  return (
    <BaseEmptyState
      icon={icon}
      title={title}
      description={description}
      action={action}
      actionLabel={actionLabel}
    />
  )
}
