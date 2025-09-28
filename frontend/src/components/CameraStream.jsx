import { useEffect, useMemo, useRef, useState } from 'react'
import { AspectRatio, Box, Center, Spinner, Text } from '@chakra-ui/react'

function resolveApiV1(baseOverride) {
  // 1) prioridade: override explícito
  if (baseOverride) return baseOverride.replace(/\/$/, '')
  // 2) env do Vite (ex.: http://localhost:8000/api/v1)
  const envUrl = import.meta.env.VITE_API_URL
  if (envUrl) return envUrl.replace(/\/$/, '')
  // 3) fallback: mesma origem + /api/v1
  return `${window.location.origin}/api/v1`
}

export default function CameraStream({
  cameraId,
  online = true,
  ratio = 16 / 9,
  apiBase,            // opcional, para sobrescrever base
  autoRetry = true,
  retryDelays = [1000, 2000, 5000], // ms
  borderRadius = 'md',
}) {
  const [imgSrc, setImgSrc] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const retryIndexRef = useRef(0)
  const imgRef = useRef(null)
  const mountedRef = useRef(false)

  const API_V1 = useMemo(() => resolveApiV1(apiBase), [apiBase])

  const buildUrl = () => {
    // Garante que terminamos com /api/v1 e não /api/v1/
    const base = API_V1.replace(/\/$/, '')
    const token = Date.now()
    return `${base}/cameras/${cameraId}/stream?t=${token}`
  }

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      // limpa o src para fechar a conexão MJPEG
      if (imgRef.current) imgRef.current.src = ''
    }
  }, [])

  useEffect(() => {
    // Sempre que id/online muda, reseta estado e (re)carrega
    setLoading(true)
    setError(null)
    retryIndexRef.current = 0

    if (!online) {
      setImgSrc('')
      setLoading(false)
      return
    }

    setImgSrc(buildUrl())
  }, [cameraId, online, API_V1])

  const onLoad = () => {
    if (!mountedRef.current) return
    setLoading(false)
    setError(null)
    retryIndexRef.current = 0
  }

  const tryScheduleRetry = () => {
    if (!mountedRef.current || !autoRetry) return
    const i = Math.min(retryIndexRef.current, retryDelays.length - 1)
    const delay = retryDelays[i]
    retryIndexRef.current = Math.min(i + 1, retryDelays.length - 1)
    setTimeout(() => {
      if (!mountedRef.current) return
      setImgSrc(buildUrl())
      setLoading(true)
    }, delay)
  }

  const onError = () => {
    if (!mountedRef.current) return
    setError('Falha ao carregar stream')
    tryScheduleRetry()
  }

  if (!online) {
    return (
      <AspectRatio ratio={ratio} rounded={borderRadius} bg="gray.900" color="gray.400">
        <Center><Text>Sem stream disponível</Text></Center>
      </AspectRatio>
    )
  }

  return (
    <AspectRatio ratio={ratio} rounded={borderRadius} overflow="hidden" bg="black" position="relative">
      <>
        {loading && (
          <Center position="absolute" inset={0}>
            <Spinner color="blue.400" />
          </Center>
        )}
        {error && (
          <Box position="absolute" inset={0} p={2}>
            <Text fontSize="xs" color="red.300">{error}</Text>
          </Box>
        )}
        {/* img para MJPEG */}
        <img
          ref={imgRef}
          src={imgSrc}
          onLoad={onLoad}
          onError={onError}
          alt={`camera-${cameraId}`}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
      </>
    </AspectRatio>
  )
}