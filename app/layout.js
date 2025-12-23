import { Inter } from 'next/font/google'
import './globals.css'
import { Toaster } from '@/components/ui/sonner'
import { ThemeProvider } from 'next-themes'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Inbox Copilot',
  description: 'Tu parles, je gère tes mails',
}

export default function RootLayout({ children }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body className={`${inter.className}`}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
          {children}
          <Toaster 
            position="top-center"
            toastOptions={{
              style: {
                background: 'white',
              },
              classNames: {
                success: 'bg-red-50 text-red-900 border-red-200',
                error: 'bg-red-50 text-red-900 border-red-200',
              }
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  )
}
