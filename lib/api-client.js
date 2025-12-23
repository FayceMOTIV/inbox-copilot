'use client'

import { createContext, useContext, useState, useCallback } from 'react'

// API Error Context
const ApiErrorContext = createContext(null)

// Last API error storage (in-memory, SSR-safe)
let lastApiError = null

export function ApiErrorProvider({ children }) {
  const [error, setError] = useState(null)

  const captureError = useCallback((err) => {
    const errorData = {
      message: err.message || String(err),
      endpoint: err.endpoint || 'unknown',
      status: err.status || null,
      timestamp: new Date().toISOString()
    }
    lastApiError = errorData
    setError(errorData)

    // Persist to sessionStorage (SSR-safe)
    if (typeof window !== 'undefined') {
      try {
        sessionStorage.setItem('lastApiError', JSON.stringify(errorData))
      } catch (e) {
        // Ignore storage errors
      }
    }
  }, [])

  const clearError = useCallback(() => {
    lastApiError = null
    setError(null)
    if (typeof window !== 'undefined') {
      try {
        sessionStorage.removeItem('lastApiError')
      } catch (e) {
        // Ignore
      }
    }
  }, [])

  return (
    <ApiErrorContext.Provider value={{ error, captureError, clearError }}>
      {children}
    </ApiErrorContext.Provider>
  )
}

export function useApiError() {
  const context = useContext(ApiErrorContext)
  if (!context) {
    // Return dummy if outside provider
    return { error: null, captureError: () => {}, clearError: () => {} }
  }
  return context
}

// Get last error (for debug page)
export function getLastApiError() {
  if (lastApiError) return lastApiError

  // Try sessionStorage
  if (typeof window !== 'undefined') {
    try {
      const stored = sessionStorage.getItem('lastApiError')
      if (stored) {
        return JSON.parse(stored)
      }
    } catch (e) {
      // Ignore
    }
  }
  return null
}

// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

// Wrapped fetch with error capture
export async function apiFetch(endpoint, options = {}, captureError = null) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`

  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    })

    if (!res.ok) {
      const error = new Error(`API error: ${res.status} ${res.statusText}`)
      error.status = res.status
      error.endpoint = endpoint
      if (captureError) captureError(error)
      throw error
    }

    return res
  } catch (err) {
    // Capture network errors
    if (!err.status) {
      err.endpoint = endpoint
      err.status = 0
      err.message = err.message || 'Network error'
    }
    if (captureError) captureError(err)
    throw err
  }
}

// Export API base for debug
export function getApiBase() {
  return API_BASE
}
