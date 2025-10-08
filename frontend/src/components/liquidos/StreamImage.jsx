import { useEffect, useState } from 'react'
import { Box, Spinner, Text } from '@chakra-ui/react'

// mode: 'mjpeg' (somente stream) | 'mjpeg+snapshot' (fallback alternando)
// firstTryAfterPreamble: ao montar, espera a soma dos backoffs até o máximo e só então faz a primeira tentativa
export default function StreamImage({ cameraId, height = 360, onReady, apiUrl = '/api/v1', mode = 'mjpeg', retryBaseMs = 800, retryMaxMs = 4000, firstTryAfterPreamble = true }) {
  const [src, setSrc] = useState(`${apiUrl}/streams/camera/${cameraId}`)
  const [triedSnapshot, setTriedSnapshot] = useState(false)
  const [error, setError] = useState(false)
  const [retries, setRetries] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const [timerId, setTimerId] = useState(null)

  const cameraUrl = () => `${apiUrl}/streams/camera/${cameraId}?t=${Date.now()}`
  const snapshotUrl = () => `${apiUrl}/streams/snapshot/${cameraId}?t=${Date.now()}`

  const computePreambleDelay = () => {
    // Soma 800, 1600, 3200, ... até atingir retryMaxMs (inclui retryMaxMs uma vez)
    let sum = 0
    let d = retryBaseMs
    if (d <= 0) return retryMaxMs
    const visited = new Set()
    while (true) {
      const key = Math.min(d, retryMaxMs)
      if (visited.has(key)) break
      sum += key
      visited.add(key)
      if (key === retryMaxMs) break
      d = Math.min(d * 2, retryMaxMs)
    }
    return sum
  }

  // Reset when cameraId changes
  useEffect(() => {
    // cleanup de timer pendente
    if (timerId) {
      clearTimeout(timerId)
    }
    setTriedSnapshot(false)
    setError(false)
    setRetries(0)
    setLoaded(false)
    if (firstTryAfterPreamble) {
      setSrc('') // não dispara request até o preâmbulo
      const pre = computePreambleDelay()
      const id = setTimeout(() => {
        setSrc(cameraUrl())
      }, pre)
      setTimerId(id)
      try { console.log('[StreamImage] preflight delay', { cameraId, pre }) } catch (_) {}
    } else {
      // Sempre faz cache-bust ao resetar
      setSrc(cameraUrl())
      try { console.log('[StreamImage] reset for camera', cameraId) } catch (_) {}
    }
    return () => {
      if (timerId) clearTimeout(timerId)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraId, apiUrl, firstTryAfterPreamble, retryBaseMs, retryMaxMs])

  const onError = () => {
    const next = retries + 1
    setRetries(next)
    // Mantém overlay de loading; não marcar erro para não esconder overlay
    setError(false)
    const ts = Date.now()
    // Após a primeira tentativa, usar sempre retryMaxMs (ex.: 4000ms)
    const delay = retryMaxMs
    if (mode === 'mjpeg') {
      // Apenas re-tenta MJPEG com backoff exponencial
      setTimeout(() => {
        setSrc(`${apiUrl}/streams/camera/${cameraId}?t=${ts}`)
        try { console.warn('[StreamImage] mjpeg retry', { cameraId, try: next, delay }) } catch (_) {}
      }, delay)
      return;
    }
    // Fallback alternando entre MJPEG e snapshot
    if (!triedSnapshot) {
      setTimeout(() => {
        setSrc(snapshotUrl())
        setTriedSnapshot(true)
        try { console.warn('[StreamImage] mjpeg failed, switching to snapshot', { cameraId, try: next }) } catch (_) {}
      }, delay)
    } else {
      setTimeout(() => {
        setSrc(cameraUrl())
        setTriedSnapshot(false)
        try { console.warn('[StreamImage] snapshot failed, switching back to mjpeg', { cameraId, try: next }) } catch (_) {}
      }, delay)
    }
  }

  return (
    <Box borderWidth="1px" borderRadius="md" overflow="hidden" style={{ position: 'relative' }}>
      <img
        src={src}
        onError={onError}
        onLoad={() => {
          setLoaded(true)
          setError(false)
          try { console.log('[StreamImage] loaded', { cameraId, src }) } catch (_) {}
          if (typeof onReady === 'function') onReady(cameraId)
        }}
        alt=""
        aria-hidden={!loaded}
        style={{
          display: 'block',
          width: '100%',
          height: `${height}px`,
          objectFit: 'contain',
          background: 'var(--chakra-colors-bg-subtle)',
          opacity: loaded ? 1 : 0,
        }}
      />
      {!loaded && (
        <Box
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            background: 'rgba(0,0,0,0.35)',
          }}
        >
          <Spinner size="md" color="white" />
          <Text style={{ color: 'white', fontWeight: 600 }}>Aguardando stream...</Text>
        </Box>
      )}
    </Box>
  )
}
