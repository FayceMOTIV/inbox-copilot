'use client'

import { useState, useEffect } from 'react'
import { Bell, Check, CheckCheck, AlertCircle, FileText, Mail, Star, Clock, X, RefreshCw } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useMediaQuery } from '@/hooks/use-mobile'
import { NotificationListSkeleton } from '@/components/Skeletons'
import { EmptyNotifications } from '@/components/EmptyStates'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function NotificationCenter({ onSelectEmail, onSelectThread }) {
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [open, setOpen] = useState(false)
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const isMobile = useMediaQuery('(max-width: 768px)')

  const fetchNotifications = async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true)
      const res = await fetch(`${API_BASE}/api/notifications?limit=20&user_id=default_user`)
      if (res.ok) {
        const data = await res.json()
        setNotifications(data.notifications || [])
        setUnreadCount(data.unread_count || 0)
      }
    } catch (error) {
      console.error('Error fetching notifications:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchNotifications()
    const interval = setInterval(fetchNotifications, 120000)
    return () => clearInterval(interval)
  }, [])

  const markAsRead = async (notificationId) => {
    try {
      await fetch(`${API_BASE}/api/notifications/${notificationId}/read`, {
        method: 'POST'
      })
      setNotifications(prev =>
        prev.map(n => n.id === notificationId || n._id === notificationId ? { ...n, read: true } : n)
      )
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch (error) {
      console.error('Error marking as read:', error)
    }
  }

  const markAllAsRead = async () => {
    try {
      await fetch(`${API_BASE}/api/notifications/mark_all_read?user_id=default_user`, {
        method: 'POST'
      })
      setNotifications(prev => prev.map(n => ({ ...n, read: true })))
      setUnreadCount(0)
    } catch (error) {
      console.error('Error marking all as read:', error)
    }
  }

  const handleNotificationClick = (notification) => {
    if (!notification.read) {
      markAsRead(notification.id || notification._id)
    }

    // Open relevant drawer/page based on notification type
    if (notification.data?.email_id && onSelectEmail) {
      onSelectEmail({
        email_id: notification.data.email_id,
        account_id: notification.data.account_id,
        subject: notification.body || notification.message,
        from: notification.title?.replace(/^[🔴⭐📄⏰]\s*\w+:\s*/, ''),
        is_vip: notification.data?.is_vip,
        priority: notification.priority
      })
    } else if (notification.data?.thread_id && onSelectThread) {
      onSelectThread(notification.data.thread_id)
    }

    setOpen(false)
    setMobileSheetOpen(false)
  }

  const getIcon = (type, priority) => {
    if (type === 'urgent' || priority === 'urgent') {
      return <AlertCircle className="w-4 h-4 text-red-500" />
    }
    if (type === 'vip') {
      return <Star className="w-4 h-4 text-amber-500" />
    }
    if (type === 'document') {
      return <FileText className="w-4 h-4 text-purple-500" />
    }
    if (type === 'waiting_overdue') {
      return <Clock className="w-4 h-4 text-blue-500" />
    }
    return <Mail className="w-4 h-4 text-gray-500" />
  }

  const getPriorityColor = (priority, type) => {
    if (type === 'urgent' || priority === 'urgent') return 'bg-red-50 dark:bg-red-950/30'
    if (type === 'vip') return 'bg-amber-50 dark:bg-amber-950/30'
    if (type === 'document') return 'bg-purple-50 dark:bg-purple-950/30'
    if (type === 'waiting_overdue') return 'bg-blue-50 dark:bg-blue-950/30'
    return 'bg-gray-50 dark:bg-gray-950/30'
  }

  const formatTime = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now - date
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 60) return `${minutes}min`
    if (hours < 24) return `${hours}h`
    if (days < 7) return `${days}j`
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
  }

  const NotificationList = () => (
    <>
      {loading ? (
        <NotificationListSkeleton count={4} />
      ) : notifications.length === 0 ? (
        <EmptyNotifications />
      ) : (
        <div className="space-y-1 p-2">
          {notifications.map((notification) => (
            <motion.div
              key={notification.id || notification._id}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              whileTap={{ scale: 0.98 }}
              className={`p-3 rounded-xl cursor-pointer transition-all hover:shadow-md active:bg-gray-100 dark:active:bg-gray-800 ${
                notification.read
                  ? 'opacity-60'
                  : getPriorityColor(notification.priority, notification.type)
              } ${!notification.read ? 'border-l-4 border-primary' : ''}`}
              onClick={() => handleNotificationClick(notification)}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${getPriorityColor(notification.priority, notification.type)}`}>
                  {getIcon(notification.type, notification.priority)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-sm truncate">
                      {notification.title?.replace(/^[🔴⭐📄⏰]\s*/, '')}
                    </span>
                    <span className="text-xs text-muted-foreground flex-shrink-0">
                      {formatTime(notification.created_at)}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                    {notification.message || notification.body}
                  </p>
                  {notification.data?.reason && (
                    <Badge variant="outline" className="mt-2 text-xs">
                      {notification.data.reason}
                    </Badge>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </>
  )

  // Mobile: Bottom Sheet
  if (isMobile) {
    return (
      <>
        <Button
          variant="ghost"
          size="icon"
          className="relative rounded-full"
          onClick={() => setMobileSheetOpen(true)}
        >
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </motion.span>
          )}
        </Button>

        <AnimatePresence>
          {mobileSheetOpen && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/40 z-50"
                onClick={() => setMobileSheetOpen(false)}
              />
              <motion.div
                initial={{ y: '100%' }}
                animate={{ y: 0 }}
                exit={{ y: '100%' }}
                transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                className="fixed inset-x-0 bottom-0 z-50 bg-white dark:bg-card rounded-t-3xl max-h-[85vh] overflow-hidden"
              >
                <div className="flex justify-center pt-3 pb-2">
                  <div className="w-12 h-1.5 bg-gray-300 rounded-full" />
                </div>
                <div className="flex items-center justify-between px-4 pb-3 border-b">
                  <h3 className="text-lg font-bold">Notifications</h3>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="rounded-full h-9 w-9"
                      onClick={() => fetchNotifications(true)}
                      disabled={refreshing}
                    >
                      <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                    </Button>
                    {unreadCount > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs h-9"
                        onClick={markAllAsRead}
                      >
                        <CheckCheck className="w-4 h-4 mr-1" />
                        Tout lire
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="rounded-full h-9 w-9"
                      onClick={() => setMobileSheetOpen(false)}
                    >
                      <X className="w-5 h-5" />
                    </Button>
                  </div>
                </div>
                <ScrollArea className="h-[60vh]">
                  <NotificationList />
                </ScrollArea>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </>
    )
  }

  // Desktop: Dropdown
  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative rounded-full"
        >
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </motion.span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-96">
        <div className="flex items-center justify-between px-3 py-2">
          <DropdownMenuLabel className="p-0 text-sm font-bold">
            Notifications
          </DropdownMenuLabel>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={(e) => {
                e.preventDefault()
                markAllAsRead()
              }}
            >
              <CheckCheck className="w-3 h-3 mr-1" />
              Tout lire
            </Button>
          )}
        </div>
        <DropdownMenuSeparator />

        <ScrollArea className="h-[400px]">
          <NotificationList />
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
