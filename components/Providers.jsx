'use client'

import { ThemeProvider } from 'next-themes'
import { ApiErrorProvider } from '@/lib/api-client'

export default function Providers({ children }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <ApiErrorProvider>
        {children}
      </ApiErrorProvider>
    </ThemeProvider>
  )
}
