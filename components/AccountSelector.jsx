'use client'

import { useState, useEffect } from 'react'
import { ChevronDown, Mail, Check, RefreshCw } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export default function AccountSelector({
  accounts = [],
  selectedAccountId,
  onSelect,
  showAllOption = true,
  loading = false
}) {
  const selectedAccount = accounts.find(a => a.account_id === selectedAccountId)

  const getProviderIcon = (provider) => {
    if (provider === 'gmail' || provider === 'google') {
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24">
          <path fill="#EA4335" d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"/>
        </svg>
      )
    }
    if (provider === 'microsoft' || provider === 'outlook') {
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24">
          <path fill="#0078D4" d="M0 0h11.377v11.372H0zm12.623 0H24v11.372H12.623zM0 12.623h11.377V24H0zm12.623 0H24V24H12.623z"/>
        </svg>
      )
    }
    return <Mail className="w-4 h-4" />
  }

  const getDisplayName = (account) => {
    if (!account) return 'Tous les comptes'
    const email = account.email || ''
    const name = account.name || email.split('@')[0]
    return name
  }

  const getDisplayEmail = (account) => {
    return account?.email || ''
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="h-9 px-3 gap-2 bg-background/50 border-border/50 hover:bg-background/80"
          disabled={loading}
        >
          {loading ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : selectedAccount ? (
            getProviderIcon(selectedAccount.provider || selectedAccount.type)
          ) : (
            <Mail className="w-4 h-4 text-muted-foreground" />
          )}
          <span className="max-w-[120px] truncate text-sm">
            {getDisplayName(selectedAccount)}
          </span>
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Sélectionner un compte
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {showAllOption && (
          <DropdownMenuItem
            onClick={() => onSelect(null)}
            className="flex items-center gap-2 cursor-pointer"
          >
            <Mail className="w-4 h-4 text-muted-foreground" />
            <div className="flex-1">
              <div className="font-medium">Tous les comptes</div>
              <div className="text-xs text-muted-foreground">
                {accounts.length} compte{accounts.length > 1 ? 's' : ''} connecté{accounts.length > 1 ? 's' : ''}
              </div>
            </div>
            {!selectedAccountId && (
              <Check className="w-4 h-4 text-primary" />
            )}
          </DropdownMenuItem>
        )}

        {showAllOption && accounts.length > 0 && <DropdownMenuSeparator />}

        {accounts.map((account) => (
          <DropdownMenuItem
            key={account.account_id}
            onClick={() => onSelect(account.account_id)}
            className="flex items-center gap-2 cursor-pointer"
          >
            {getProviderIcon(account.provider || account.type)}
            <div className="flex-1 min-w-0">
              <div className="font-medium truncate">{getDisplayName(account)}</div>
              <div className="text-xs text-muted-foreground truncate">
                {getDisplayEmail(account)}
              </div>
            </div>
            {selectedAccountId === account.account_id && (
              <Check className="w-4 h-4 text-primary flex-shrink-0" />
            )}
          </DropdownMenuItem>
        ))}

        {accounts.length === 0 && (
          <div className="px-2 py-4 text-center text-sm text-muted-foreground">
            Aucun compte connecté
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
