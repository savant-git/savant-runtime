import {
  MutableRefObject,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react"

type SpeechRecognitionEventLike = Event & {
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string
      }
      isFinal: boolean
      length: number
    }
    length: number
  }
}

type SpeechRecognitionErrorLike = Event & {
  error?: string
  message?: string
}

type RecognitionInstance = {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  abort: () => void
  onstart: (() => void) | null
  onend: (() => void) | null
  onerror:
    | ((event: SpeechRecognitionErrorLike) => void)
    | null
  onresult:
    | ((event: SpeechRecognitionEventLike) => void)
    | null
}

type RecognitionConstructor = new () => RecognitionInstance

declare global {
  interface Window {
    SpeechRecognition?: RecognitionConstructor
    webkitSpeechRecognition?: RecognitionConstructor
  }
}

export type PalaverVoiceState = {
  supported: boolean
  listening: boolean
  interim: string
  error: string
  start: () => void
  stop: () => void
  toggle: () => void
  clearError: () => void
}

export function usePalaverVoice(
  onFinal: (text: string) => void,
): PalaverVoiceState {
  const recognitionRef:
    MutableRefObject<
      RecognitionInstance | null
    > = useRef(null)

  const onFinalRef = useRef(onFinal)

  const [supported, setSupported] =
    useState(false)

  const [listening, setListening] =
    useState(false)

  const [interim, setInterim] =
    useState("")

  const [error, setError] =
    useState("")

  useEffect(() => {
    onFinalRef.current = onFinal
  }, [onFinal])

  useEffect(() => {
    const Constructor =
      window.SpeechRecognition ??
      window.webkitSpeechRecognition

    if (!Constructor) {
      setSupported(false)
      return
    }

    setSupported(true)

    const recognition =
      new Constructor()

    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang =
      navigator.language || "en-US"

    recognition.onstart = () => {
      setListening(true)
      setInterim("")
      setError("")
    }

    recognition.onend = () => {
      setListening(false)
      setInterim("")
    }

    recognition.onerror = (
      event,
    ) => {
      setListening(false)
      setInterim("")

      setError(
        event.error ||
          event.message ||
          "voice input failed",
      )
    }

    recognition.onresult = (
      event,
    ) => {
      let interimText = ""
      let finalText = ""

      for (
        let index = 0;
        index < event.results.length;
        index += 1
      ) {
        const result =
          event.results[index]

        const transcript =
          result[0]?.transcript ?? ""

        if (result.isFinal) {
          finalText += transcript
        } else {
          interimText += transcript
        }
      }

      setInterim(
        interimText.trim(),
      )

      const normalized =
        finalText.trim()

      if (normalized) {
        onFinalRef.current(
          normalized,
        )
      }
    }

    recognitionRef.current =
      recognition

    return () => {
      recognition.abort()
      recognitionRef.current = null
    }
  }, [])

  const start = useCallback(() => {
    if (
      !supported ||
      listening ||
      !recognitionRef.current
    ) {
      return
    }

    try {
      recognitionRef.current.start()
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "voice input failed",
      )
    }
  }, [
    listening,
    supported,
  ])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
  }, [])

  const toggle = useCallback(() => {
    if (listening) {
      stop()
    } else {
      start()
    }
  }, [
    listening,
    start,
    stop,
  ])

  const clearError =
    useCallback(() => {
      setError("")
    }, [])

  return {
    supported,
    listening,
    interim,
    error,
    start,
    stop,
    toggle,
    clearError,
  }
}
