'use client'

import { cn } from '@/lib/utils'

// Base skeleton with shimmer animation
export function Skeleton({ className, ...props }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 dark:from-gray-800 dark:via-gray-700 dark:to-gray-800 bg-[length:200%_100%]",
        className
      )}
      {...props}
    />
  )
}

// Email card skeleton
export function EmailCardSkeleton() {
  return (
    <div className="p-4 rounded-xl border border-border bg-card">
      <div className="flex items-start gap-3">
        <Skeleton className="w-10 h-10 rounded-lg flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-12 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-3 w-1/2" />
        </div>
        <Skeleton className="w-5 h-5 rounded flex-shrink-0" />
      </div>
    </div>
  )
}

// Email list skeleton
export function EmailListSkeleton({ count = 3 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <EmailCardSkeleton key={i} />
      ))}
    </div>
  )
}

// Document card skeleton
export function DocumentCardSkeleton() {
  return (
    <div className="p-4 rounded-xl border border-border bg-card">
      <div className="flex items-start gap-3">
        <Skeleton className="w-12 h-12 rounded-lg flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      </div>
    </div>
  )
}

// Notification skeleton
export function NotificationSkeleton() {
  return (
    <div className="p-3 rounded-xl">
      <div className="flex items-start gap-3">
        <Skeleton className="w-9 h-9 rounded-lg flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-10" />
          </div>
          <Skeleton className="h-3 w-full" />
        </div>
      </div>
    </div>
  )
}

// Notification list skeleton
export function NotificationListSkeleton({ count = 4 }) {
  return (
    <div className="space-y-2 p-2">
      {Array.from({ length: count }).map((_, i) => (
        <NotificationSkeleton key={i} />
      ))}
    </div>
  )
}

// VIP card skeleton
export function VIPCardSkeleton() {
  return (
    <div className="p-4 rounded-2xl border border-border bg-card">
      <div className="flex items-center gap-4">
        <Skeleton className="w-14 h-14 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-48" />
          <div className="flex gap-2 pt-1">
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  )
}

// Recap section skeleton
export function RecapSectionSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Skeleton className="w-8 h-8 rounded-lg" />
        <Skeleton className="h-6 w-40" />
      </div>
      <EmailListSkeleton count={2} />
    </div>
  )
}

// Full page loading skeleton
export function PageLoadingSkeleton() {
  return (
    <div className="p-4 space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-10 rounded-full" />
      </div>
      <RecapSectionSkeleton />
      <RecapSectionSkeleton />
    </div>
  )
}

// Chat message skeleton
export function ChatMessageSkeleton({ isUser = false }) {
  return (
    <div className={cn(
      "flex gap-2 items-end",
      isUser ? "justify-end" : "justify-start"
    )}>
      <div className={cn(
        "max-w-[75%] rounded-3xl px-5 py-3.5",
        isUser ? "bg-primary/20" : "bg-secondary"
      )}>
        <div className="space-y-2">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
    </div>
  )
}

// Stats card skeleton
export function StatsCardSkeleton() {
  return (
    <div className="p-4 rounded-2xl border border-border bg-card">
      <div className="flex items-center gap-3">
        <Skeleton className="w-12 h-12 rounded-xl" />
        <div className="space-y-2">
          <Skeleton className="h-6 w-16" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>
    </div>
  )
}
