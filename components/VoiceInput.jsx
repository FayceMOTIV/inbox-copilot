'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Volume2, VolumeX, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { toast } from 'sonner'

// Check browser support
const isSpeechRecognitionSupported = () => {
  if (typeof window === 'undefined') return false
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition)
}

const isSpeechSynthesisSupported = () => {
  if (typeof window === 'undefined') return false
  return !!window.speechSynthesis
}

// Voice Input Button (STT)
export function VoiceInputButton({ onTranscript, disabled = false, className = '' }) {
  const [isListening, setIsListening] = useState(false)
  const [isSupported, setIsSupported] = useState(false)
  const recognitionRef = useRef(null)

  useEffect(() => {
    setIsSupported(isSpeechRecognitionSupported())

    if (isSpeechRecognitionSupported()) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = false
      recognitionRef.current.interimResults = false
      recognitionRef.current.lang = 'fr-FR'

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        onTranscript?.(transcript)
        setIsListening(false)
        toast.success('Message transcrit')
      }

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error)
        if (event.error !== 'aborted') {
          toast.error('Erreur de reconnaissance vocale')
        }
        setIsListening(false)
      }

      recognitionRef.current.onend = () => {
        setIsListening(false)
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
    }
  }, [onTranscript])

  const toggleListening = () => {
    if (!isSupported) {
      toast.error('Dictée vocale non disponible sur ce navigateur')
      return
    }

    if (isListening) {
      recognitionRef.current?.stop()
      setIsListening(false)
    } else {
      try {
        recognitionRef.current?.start()
        setIsListening(true)
        toast('Écoute en cours...', { icon: '🎤' })
      } catch (error) {
        console.error('Failed to start recognition:', error)
        toast.error('Impossible de démarrer la dictée')
      }
    }
  }

  if (!isSupported) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              disabled
              className={`rounded-full opacity-50 ${className}`}
            >
              <MicOff className="w-5 h-5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Dictée vocale non disponible</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleListening}
            disabled={disabled}
            className={`rounded-full transition-all ${
              isListening
                ? 'bg-red-500 text-white hover:bg-red-600 animate-pulse'
                : ''
            } ${className}`}
          >
            <AnimatePresence mode="wait">
              {isListening ? (
                <motion.div
                  key="listening"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0 }}
                >
                  <MicOff className="w-5 h-5" />
                </motion.div>
              ) : (
                <motion.div
                  key="idle"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0 }}
                >
                  <Mic className="w-5 h-5" />
                </motion.div>
              )}
            </AnimatePresence>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{isListening ? 'Arrêter la dictée' : 'Dictée vocale'}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

// TTS Toggle Button
export function TTSToggleButton({ enabled, onToggle, className = '' }) {
  const [isSupported, setIsSupported] = useState(false)

  useEffect(() => {
    setIsSupported(isSpeechSynthesisSupported())
  }, [])

  if (!isSupported) {
    return null
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className={`rounded-full transition-all ${
              enabled
                ? 'bg-indigo-100 text-indigo-600 hover:bg-indigo-200 dark:bg-indigo-900/50'
                : ''
            } ${className}`}
          >
            {enabled ? (
              <Volume2 className="w-5 h-5" />
            ) : (
              <VolumeX className="w-5 h-5" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{enabled ? 'Désactiver la lecture' : 'Lire les réponses'}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

// TTS Speaker function
export function useTTS() {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isSupported, setIsSupported] = useState(false)

  useEffect(() => {
    setIsSupported(isSpeechSynthesisSupported())
  }, [])

  const speak = (text, options = {}) => {
    if (!isSupported || !text) return

    // Cancel any ongoing speech
    window.speechSynthesis.cancel()

    // If text is too long, summarize
    let textToSpeak = text
    if (text.length > 200) {
      // Extract first sentence or truncate
      const firstSentence = text.split(/[.!?]/)[0]
      textToSpeak = firstSentence.length > 10 ? firstSentence : text.slice(0, 150)
      textToSpeak += '...'
    }

    const utterance = new SpeechSynthesisUtterance(textToSpeak)
    utterance.lang = options.lang || 'fr-FR'
    utterance.rate = options.rate || 1.0
    utterance.pitch = options.pitch || 1.0

    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    window.speechSynthesis.speak(utterance)
  }

  const stop = () => {
    if (isSupported) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
    }
  }

  return { speak, stop, isSpeaking, isSupported }
}

// Listening animation overlay
export function ListeningOverlay({ isActive }) {
  return (
    <AnimatePresence>
      {isActive && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/20 z-40 flex items-center justify-center"
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            className="bg-white dark:bg-card p-8 rounded-3xl shadow-2xl flex flex-col items-center"
          >
            <motion.div
              animate={{
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
              className="w-20 h-20 bg-gradient-to-br from-red-500 to-orange-500 rounded-full flex items-center justify-center mb-4"
            >
              <Mic className="w-10 h-10 text-white" />
            </motion.div>
            <p className="text-lg font-semibold">Écoute en cours...</p>
            <p className="text-sm text-muted-foreground mt-1">Parlez maintenant</p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
