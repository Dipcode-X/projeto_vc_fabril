import { useEffect, useState } from 'react'
import { Box, Heading, Text, SimpleGrid, Badge, Flex, HStack, Spinner, Button, IconButton } from '@chakra-ui/react'
import { toaster } from '../toaster.js'
import { useParams } from 'react-router-dom'
import ErrorBoundary from '../components/ErrorBoundary.jsx'

const API_URL = '/api/v1'

function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1)
}

function normalize(str) {
  return (str || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

function safeText(val, fallback = '—') {
  if (val === null || val === undefined) return fallback
  const t = typeof val
  if (t === 'string' || t === 'number' || t === 'boolean') return String(val)
  try { return JSON.stringify(val) }
  catch { return fallback }
}

// Locale-aware number parsing helpers (hoisted function declarations)
function parseNumLocale(v) {
  if (v === '' || v === null || v === undefined) return null
  const s = String(v).trim().replace(',', '.')
  const n = Number(s)
  return Number.isFinite(n) ? n : null
}
function valid01(v) {
  const n = parseNumLocale(v)
  return n !== null && n >= 0 && n <= 1
}

// Exibe MJPEG e faz fallback para snapshot se falhar
function StreamImage({ cameraId, height = 160, onReady }) {
  const [src, setSrc] = useState(`${API_URL}/streams/camera/${cameraId}`)
  const [triedSnapshot, setTriedSnapshot] = useState(false)
  const [error, setError] = useState(false)

  const onError = () => {
    if (!triedSnapshot) {
      setSrc(`${API_URL}/streams/snapshot/${cameraId}`)
      setTriedSnapshot(true)
    } else {
      setError(true)
    }
  }

  if (error) {
    return (
      <Box borderWidth="1px" borderRadius="md" h={`${height}px`} bg="bg.subtle" display="flex" alignItems="center" justifyContent="center">
        <Text fontSize="sm" color="fg.muted">Sem stream disponível</Text>
      </Box>
    )
  }

  return (
    <Box borderWidth="1px" borderRadius="md" overflow="hidden">
      <img
        src={src}
        onError={onError}
        onLoad={() => { if (typeof onReady === 'function') onReady() }}
        alt={`camera-${cameraId}`}
        style={{ display: 'block', width: '100%', height: `${height}px`, objectFit: 'contain', background: 'var(--chakra-colors-bg-subtle)' }}
      />
    </Box>
  )
}

function CameraCard({ camera, produtos, onAfterChange }) {
  const baseOnline = ['active', 'online', 'running', true].includes((camera?.status || '').toString().toLowerCase())
  const [statusInfo, setStatusInfo] = useState(null)
  const [statusError, setStatusError] = useState(null)
  // Modelos YOLO ativos (runtime)
  const [modelsInfo, setModelsInfo] = useState(null)

  // Toaster, createToaster indisponível nesta versão do Chakra; usando alert/console
  const [selectedProdutoId, setSelectedProdutoId] = useState(camera?.produto_id || null)
  useEffect(() => { setSelectedProdutoId(camera?.produto_id || null) }, [camera?.produto_id])
  const [applying, setApplying] = useState(false)
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [streamReady, setStreamReady] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [thrRoi, setThrRoi] = useState('')
  const [thrItem, setThrItem] = useState('')
  const [thrDiv, setThrDiv] = useState('')
  const [thrRoiDirty, setThrRoiDirty] = useState(false)
  const [thrItemDirty, setThrItemDirty] = useState(false)
  const [thrDivDirty, setThrDivDirty] = useState(false)
  const [draftInitialized, setDraftInitialized] = useState(false)
  const [savingThr, setSavingThr] = useState(false)
  const [restoringThr, setRestoringThr] = useState(false)
  // Draft e sujidade para chaves avançadas de thresholds (numéricas/booleanas)
  const [advDraft, setAdvDraft] = useState({})
  const [advDirty, setAdvDirty] = useState({})
  const [lastApplied, setLastApplied] = useState(null)
  // Helper para identificar chaves percentuais (0..1)
  const isPercentKey = (name) => typeof name === 'string' && name.toLowerCase().includes('percentual')

  // Helpers are module-scoped function declarations (see top)


  useEffect(() => {
    let cancelled = false
    let timerId

    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/cameras/${camera.id}/status`)
        const data = res.ok ? await res.json() : { running: false, status_message: { message: 'Processador inativo' } }
        if (!cancelled) {
          setStatusInfo(data)
          if (data?.running === true) setStarting(false)
        }
      } catch (e) {
        if (!cancelled) setStatusError(e.message)
      } finally {
        if (!cancelled) timerId = setTimeout(fetchStatus, 3000)
      }
    }

    fetchStatus()
    return () => {
      cancelled = true
      if (timerId) clearTimeout(timerId)
    }
  }, [camera.id])

  // Polling leve para modelos ativos (item_model/roi_model)
  useEffect(() => {
    let cancelled = false
    let timerId
    const fetchModels = async () => {
      try {
        const res = await fetch(`${API_URL}/cameras/${camera.id}/models`)
        const data = res.ok ? await res.json() : null
        if (!cancelled) setModelsInfo(data)
      } catch (e) {
        if (!cancelled) setModelsInfo(null)
      } finally {
        if (!cancelled) timerId = setTimeout(fetchModels, 5000)
      }
    }
    fetchModels()
    return () => { cancelled = true; if (timerId) clearTimeout(timerId) }
  }, [camera.id])

  const refreshNow = async () => {
    try {
      const [statusRes, modelsRes] = await Promise.all([
        fetch(`${API_URL}/cameras/${camera.id}/status`),
        fetch(`${API_URL}/cameras/${camera.id}/models`),
      ])
      const statusData = statusRes.ok ? await statusRes.json() : null
      const modelsData = modelsRes.ok ? await modelsRes.json() : null
      if (statusData) setStatusInfo(statusData)
      if (modelsData) setModelsInfo(modelsData)
    } catch (e) {
      // silencioso
    }
  }

  const sm = statusInfo?.status_message || {}
  const estado = sm.estado || sm.message || '—'
  const camada = sm.camada_atual ?? sm.camada ?? '—'
  const contagem = sm.contagem_atual ?? sm.contagem ?? '—'
  const isLoadingStatus = statusInfo === null && !statusError
  // Destaques: metas vindas do runtime (/cameras/{id}/models)
  const itensPorCamada = modelsInfo?.perfil_caixa?.itens_por_camada
  const totalCamadas = modelsInfo?.perfil_caixa?.total_camadas
  const requiresDivisor = modelsInfo?.requires_divisor
  // Status/labels computed early to avoid referencing before init
  const runningNow = statusInfo?.running === true
  const statusLabel = runningNow ? 'Online' : 'Offline'
  const statusColor = runningNow ? 'green' : 'red'
  const overlayLoading = starting || (runningNow && !streamReady)
  const overlayLabel = stopping ? 'Parando...' : (overlayLoading ? 'Iniciando...' : null)
  const statusLabelStr = safeText(statusLabel)
  const overlayLabelStr = overlayLabel != null ? safeText(overlayLabel) : null
  // Alterações pendentes (para confirmação ao fechar)
  const hasUnsaved = Boolean(
    thrRoiDirty || thrItemDirty || thrDivDirty || (advDirty && Object.values(advDirty).some(Boolean))
  )
  // Chaves avançadas presentes em thresholds do runtime (exclui as 3 canônicas)
  const allThresholds = modelsInfo?.thresholds || {}
  const advancedKeys = Object.keys(allThresholds).filter(k => k !== 'confianca_roi' && k !== 'confianca_item' && k !== 'confianca_divisor')
  // Mudanças pendentes e possibilidade de aplicar (guarded contra erros de inicialização)
  let canApply = false
  try {
    const curT = modelsInfo?.thresholds || {}
    const pRoi = parseNumLocale(thrRoi)
    const pItem = parseNumLocale(thrItem)
    const pDiv = parseNumLocale(thrDiv)
    const changedRoi = pRoi !== null && pRoi >= 0 && pRoi <= 1 && (typeof curT.confianca_roi !== 'number' || Math.abs(pRoi - curT.confianca_roi) > 1e-6)
    const changedItem = pItem !== null && pItem >= 0 && pItem <= 1 && (typeof curT.confianca_item !== 'number' || Math.abs(pItem - curT.confianca_item) > 1e-6)
    const changedDiv = pDiv !== null && pDiv >= 0 && pDiv <= 1 && (typeof curT.confianca_divisor !== 'number' || Math.abs(pDiv - curT.confianca_divisor) > 1e-6)
    // Verificar mudanças nas chaves avançadas (numéricas/booleanas)
    let changedAnyAdv = false
    for (const k of advancedKeys) {
      const curV = allThresholds[k]
      const dV = advDraft?.[k]
      if (typeof curV === 'number') {
        const pv = parseNumLocale(dV)
        if (pv !== null) {
          const valid = isPercentKey(k) ? (pv >= 0 && pv <= 1) : (pv >= 0)
          if (valid && (typeof curV !== 'number' || Math.abs(pv - curV) > 1e-6)) { changedAnyAdv = true; break }
        }
      } else if (typeof curV === 'boolean') {
        if (typeof dV === 'boolean' && dV !== curV) { changedAnyAdv = true; break }
      }
    }
    canApply = runningNow && (changedRoi || changedItem || (requiresDivisor !== false && changedDiv) || changedAnyAdv)
  } catch (e) {
    try { console.error('[CameraCard] calc canApply error', e) } catch (_) {}
  }

  const applyProduto = async () => {
    if (!selectedProdutoId) return
    setApplying(true)
    try {
      const res = await fetch(`${API_URL}/cameras/${camera.id}/produto`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ produto_id: Number(selectedProdutoId) })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || data?.error || res.statusText)

      // Atualiza visão local imediatamente; pollers manterão sincronizado
      const appliedT = data?.applied_thresholds
      setModelsInfo((prev) => ({
        ...(prev || {}),
        item_model: data?.applied_models?.item_model ?? prev?.item_model ?? null,
        roi_model: data?.applied_models?.roi_model ?? prev?.roi_model ?? null,
        perfil_caixa: {
          itens_por_camada: data?.perfil_aplicado?.itens_por_camada ?? prev?.perfil_caixa?.itens_por_camada,
          total_camadas: data?.perfil_aplicado?.total_camadas ?? prev?.perfil_caixa?.total_camadas,
        },
        requires_divisor: data?.perfil_aplicado?.requires_divisor ?? prev?.requires_divisor,
        thresholds: {
          ...(prev?.thresholds || {}),
          ...(appliedT || {}),
        },
      }))
      // Se o backend retornou thresholds aplicados, refletir nos inputs e limpar dirty flags
      if (appliedT && typeof appliedT === 'object') {
        if (typeof appliedT.confianca_roi === 'number') setThrRoi(String(Number(appliedT.confianca_roi.toFixed ? appliedT.confianca_roi.toFixed(2) : appliedT.confianca_roi)))
        if (typeof appliedT.confianca_item === 'number') setThrItem(String(Number(appliedT.confianca_item.toFixed ? appliedT.confianca_item.toFixed(2) : appliedT.confianca_item)))
        if (typeof appliedT.confianca_divisor === 'number') setThrDiv(String(Number(appliedT.confianca_divisor.toFixed ? appliedT.confianca_divisor.toFixed(2) : appliedT.confianca_divisor)))
        // Atualiza drafts avançados conforme retorno e limpa dirty
        {
          const advNext = {}
          for (const k of Object.keys(appliedT)) {
            if (k === 'confianca_roi' || k === 'confianca_item' || k === 'confianca_divisor') continue
            const v = appliedT[k]
            if (typeof v === 'number') advNext[k] = String(Number(v.toFixed ? v.toFixed(2) : v))
            else if (typeof v === 'boolean') advNext[k] = Boolean(v)
          }
          if (Object.keys(advNext).length > 0) setAdvDraft(prev => ({ ...prev, ...advNext }))
          setAdvDirty({})
        }
        setThrRoiDirty(false); setThrItemDirty(false); setThrDivDirty(false)
      }
      toaster.create({ title: 'Produto aplicado', description: data?.produto_nome || '', status: 'success', duration: 3000, isClosable: true })
      // Pequeno atraso para evitar condição de corrida antes de repuxar do runtime
      await new Promise((r) => setTimeout(r, 300))
      await refreshNow()
      if (typeof onAfterChange === 'function') onAfterChange()
    } catch (e) {
      toaster.create({ title: 'Falha ao aplicar produto', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
    } finally {
      setApplying(false)
    }
  }

  const startCamera = async () => {
    setStarting(true)
    setStreamReady(false)
    try {
      const res = await fetch(`${API_URL}/cameras/${camera.id}/start`, { method: 'POST' })
      await res.json().catch(() => {})
      // Não disparar refreshNow()/onAfterChange aqui para evitar remontar o card e perder o estado `starting`.
      // O polling de /status e /models cuidará da atualização visual.
      // Sucesso imediato removido: overlay persiste até running=true via polling de /status
    } catch (e) {
      toaster.create({ title: 'Falha ao iniciar câmera', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
    } finally {
      // Não limpar `starting` aqui; overlay será removido quando running=true ou após STOP
    }
  }

  const stopCamera = async () => {
    setStopping(true)
    try {
      const res = await fetch(`${API_URL}/cameras/${camera.id}/stop`, { method: 'POST' })
      await res.json().catch(() => {})
      await refreshNow()
      if (typeof onAfterChange === 'function') onAfterChange()
      toaster.create({ title: 'Câmera parada', status: 'success', duration: 2500, isClosable: true })
    } catch (e) {
      toaster.create({ title: 'Falha ao parar', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
    } finally {
      // Garantir que um STOP durante o startup remova o overlay de "Iniciando..."
      setStarting(false)
      setStopping(false)
      setStreamReady(false)
    }
  }

  

  // Quando a câmera reportar running=true, verificar via endpoint de debug
  // se já existem frames na fila. Só então liberamos o overlay.
  useEffect(() => {
    let cancelled = false
    let timerId
    const pollDebug = async () => {
      try {
        const res = await fetch(`${API_URL}/streams/debug/${camera.id}`)
        if (res.ok) {
          const info = await res.json()
          const qsize = Number(info?.queue_size || 0)
          if (!cancelled && qsize > 0) {
            setStreamReady(true)
            return
          }
        }
      } catch (_) { /* silencioso */ }
      if (!cancelled) timerId = setTimeout(pollDebug, 500)
    }
    if (runningNow && !streamReady) {
      pollDebug()
    }
    return () => { cancelled = true; if (timerId) clearTimeout(timerId) }
  }, [runningNow, streamReady, camera.id])

  // Se a câmera deixar de rodar, resetar flag de stream
  useEffect(() => {
    if (!runningNow) setStreamReady(false)
  }, [runningNow])

  // Proteção ao sair/atualizar a página com alterações pendentes enquanto o painel está aberto
  useEffect(() => {
    if (!settingsOpen) return
    const beforeUnload = (e) => {
      if (hasUnsaved) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', beforeUnload)
    return () => window.removeEventListener('beforeunload', beforeUnload)
  }, [settingsOpen, hasUnsaved])

  // Inicializa drafts ao abrir o painel apenas uma vez; não sobrescreve enquanto o usuário edita
  useEffect(() => {
    if (!settingsOpen) return
    if (draftInitialized) return
    const t = modelsInfo?.thresholds || {}
    if (typeof t.confianca_roi === 'number') setThrRoi(String(Number(t.confianca_roi.toFixed ? t.confianca_roi.toFixed(2) : t.confianca_roi)))
    if (typeof t.confianca_item === 'number') setThrItem(String(Number(t.confianca_item.toFixed ? t.confianca_item.toFixed(2) : t.confianca_item)))
    if (typeof t.confianca_divisor === 'number') setThrDiv(String(Number(t.confianca_divisor.toFixed ? t.confianca_divisor.toFixed(2) : t.confianca_divisor)))
    // Inicializa drafts para chaves avançadas
    const advInit = {}
    for (const k of Object.keys(t)) {
      if (k === 'confianca_roi' || k === 'confianca_item' || k === 'confianca_divisor') continue
      const v = t[k]
      if (typeof v === 'number') advInit[k] = String(Number(v.toFixed ? v.toFixed(2) : v))
      else if (typeof v === 'boolean') advInit[k] = Boolean(v)
    }
    setAdvDraft(advInit)
    setAdvDirty({})
    setDraftInitialized(true)
  }, [settingsOpen, draftInitialized, modelsInfo])

  const applyThresholds = async () => {
    if (!runningNow) return

    const cur = modelsInfo?.thresholds || {}
    const pRoi = parseNumLocale(thrRoi)
    const pItem = parseNumLocale(thrItem)
    const pDiv = parseNumLocale(thrDiv)
    const changedRoi = pRoi !== null && pRoi >= 0 && pRoi <= 1 && (typeof cur.confianca_roi !== 'number' || Math.abs(pRoi - cur.confianca_roi) > 1e-6)
    const changedItem = pItem !== null && pItem >= 0 && pItem <= 1 && (typeof cur.confianca_item !== 'number' || Math.abs(pItem - cur.confianca_item) > 1e-6)
    const changedDiv = pDiv !== null && pDiv >= 0 && pDiv <= 1 && (typeof cur.confianca_divisor !== 'number' || Math.abs(pDiv - cur.confianca_divisor) > 1e-6)

    const body = {}
    if (changedRoi) body.confianca_roi = pRoi
    if (changedItem) body.confianca_item = pItem
    if (requiresDivisor !== false && changedDiv) body.confianca_divisor = pDiv
    // Adiciona chaves avançadas alteradas (numéricas/booleanas)
    for (const k of Object.keys(cur)) {
      if (k === 'confianca_roi' || k === 'confianca_item' || k === 'confianca_divisor') continue
      const curV = cur[k]
      const dV = advDraft?.[k]
      if (typeof curV === 'number') {
        const pv = parseNumLocale(dV)
        if (pv !== null) {
          const valid = isPercentKey(k) ? (pv >= 0 && pv <= 1) : (pv >= 0)
          if (valid && (typeof curV !== 'number' || Math.abs(pv - curV) > 1e-6)) {
            body[k] = pv
          }
        }
      } else if (typeof curV === 'boolean') {
        if (typeof dV === 'boolean' && dV !== curV) {
          body[k] = dV
        }
      }
    }

    if (Object.keys(body).length === 0) {
      toaster.create({ title: 'Nada para aplicar', description: 'Nenhuma alteração válida para aplicar.', status: 'info', duration: 2500, isClosable: true })
      return
    }
    setSavingThr(true)
    try {
      try { console.log('[applyThresholds] sending', body) } catch (_) {}
      const res = await fetch(`${API_URL}/cameras/${camera.id}/thresholds`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json().catch(() => ({}))
      try { console.log('[applyThresholds] response', data) } catch (_) {}
      if (!res.ok) throw new Error(data?.detail || res.statusText)
      const rt = data?.runtime_thresholds || {}
      try { console.log('[applyThresholds] runtime_thresholds', rt) } catch (_) {}
      // Atualiza modelsInfo.thresholds localmente com runtime efetivo
      setModelsInfo((prev) => {
        const prevThr = prev?.thresholds || {}
        const merged = { ...prevThr, ...(rt && typeof rt === 'object' ? rt : {}) }
        if (merged.confianca_roi === undefined && body.confianca_roi !== undefined) merged.confianca_roi = body.confianca_roi
        if (merged.confianca_item === undefined && body.confianca_item !== undefined) merged.confianca_item = body.confianca_item
        if (merged.confianca_divisor === undefined && body.confianca_divisor !== undefined) merged.confianca_divisor = body.confianca_divisor
        return { ...(prev || {}), thresholds: merged }
      })
      // Atualiza drafts avançados com valores efetivos do runtime (ou body como fallback) e limpa dirty
      {
        const keysApply = Array.from(new Set([...Object.keys(cur), ...(rt ? Object.keys(rt) : []), ...Object.keys(body)]))
          .filter(k => k !== 'confianca_roi' && k !== 'confianca_item' && k !== 'confianca_divisor')
        const advNext = {}
        for (const k of keysApply) {
          const v = (rt && Object.prototype.hasOwnProperty.call(rt, k)) ? rt[k] : (Object.prototype.hasOwnProperty.call(body, k) ? body[k] : undefined)
          if (typeof v === 'number') advNext[k] = String(Number(v.toFixed ? v.toFixed(2) : v))
          else if (typeof v === 'boolean') advNext[k] = Boolean(v)
        }
        if (Object.keys(advNext).length > 0) setAdvDraft(prev => ({ ...prev, ...advNext }))
        setAdvDirty({})
      }
      // Atualiza inputs de forma fiel ao runtime (se disponível)
      if (typeof rt.confianca_roi === 'number') setThrRoi(String(Number(rt.confianca_roi.toFixed ? rt.confianca_roi.toFixed(2) : rt.confianca_roi)))
      if (typeof rt.confianca_item === 'number') setThrItem(String(Number(rt.confianca_item.toFixed ? rt.confianca_item.toFixed(2) : rt.confianca_item)))
      if (typeof rt.confianca_divisor === 'number') setThrDiv(String(Number(rt.confianca_divisor.toFixed ? rt.confianca_divisor.toFixed(2) : rt.confianca_divisor)))
      // Após aplicar, limpa dirty flags para permitir futuras atualizações automáticas
      setThrRoiDirty(false); setThrItemDirty(false); setThrDivDirty(false)
      setLastApplied({ ts: Date.now(), vals: rt })
      {
        const parts = []
        if (body.confianca_roi !== undefined) parts.push(`ROI=${(rt.confianca_roi ?? body.confianca_roi).toFixed ? (rt.confianca_roi ?? body.confianca_roi).toFixed(2) : (rt.confianca_roi ?? body.confianca_roi)}`)
        if (body.confianca_item !== undefined) parts.push(`Item=${(rt.confianca_item ?? body.confianca_item).toFixed ? (rt.confianca_item ?? body.confianca_item).toFixed(2) : (rt.confianca_item ?? body.confianca_item)}`)
        if (body.confianca_divisor !== undefined) parts.push(`Divisor=${(rt.confianca_divisor ?? body.confianca_divisor).toFixed ? (rt.confianca_divisor ?? body.confianca_divisor).toFixed(2) : (rt.confianca_divisor ?? body.confianca_divisor)}`)
        if (parts.length) toaster.create({ title: 'Thresholds aplicados', description: parts.join(', '), status: 'success', duration: 2500, isClosable: true })
      }
    } catch (e) {
      toaster.create({ title: 'Falha ao aplicar thresholds', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
    } finally {
      setSavingThr(false)
    }
  }

  const restoreThresholds = async () => {
    if (!runningNow) return
    setRestoringThr(true)
    try {
      const produtoId = Number(camera?.produto_id || selectedProdutoId)
      if (!produtoId) throw new Error('Produto atual não encontrado')
      const res = await fetch(`${API_URL}/cameras/${camera.id}/produto`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ produto_id: produtoId }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || res.statusText)
      // Log e atualização imediata na UI com os thresholds aplicados (se retornados)
      try { console.log('[restoreThresholds] response', data) } catch (_) {}
      const appliedT = data?.applied_thresholds
      if (appliedT && typeof appliedT === 'object') {
        setModelsInfo((prev) => ({
          ...(prev || {}),
          thresholds: {
            ...(prev?.thresholds || {}),
            ...appliedT,
          },
        }))
        // Atualiza inputs visuais se disponíveis
        if (typeof appliedT.confianca_roi === 'number') setThrRoi(String(Number(appliedT.confianca_roi.toFixed ? appliedT.confianca_roi.toFixed(2) : appliedT.confianca_roi)))
        if (typeof appliedT.confianca_item === 'number') setThrItem(String(Number(appliedT.confianca_item.toFixed ? appliedT.confianca_item.toFixed(2) : appliedT.confianca_item)))
        if (typeof appliedT.confianca_divisor === 'number') setThrDiv(String(Number(appliedT.confianca_divisor.toFixed ? appliedT.confianca_divisor.toFixed(2) : appliedT.confianca_divisor)))
        // Atualiza drafts avançados conforme retorno e limpa dirty
        {
          const advNext = {}
          for (const k of Object.keys(appliedT)) {
            if (k === 'confianca_roi' || k === 'confianca_item' || k === 'confianca_divisor') continue
            const v = appliedT[k]
            if (typeof v === 'number') advNext[k] = String(Number(v.toFixed ? v.toFixed(2) : v))
            else if (typeof v === 'boolean') advNext[k] = Boolean(v)
          }
          if (Object.keys(advNext).length > 0) setAdvDraft(prev => ({ ...prev, ...advNext }))
          setAdvDirty({})
        }
        setThrRoiDirty(false); setThrItemDirty(false); setThrDivDirty(false)
      }
      // Atualiza thresholds com defaults do produto (runtime) vindo do backend
      // Pequeno atraso para evitar condição de corrida antes de repuxar do runtime
      await new Promise((r) => setTimeout(r, 300))
      await refreshNow()
    } catch (e) {
      toaster.create({ title: 'Falha ao restaurar thresholds', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
    } finally {
      setRestoringThr(false)
    }
  }

  // Fechamento com confirmação quando houver alterações pendentes
  const handleAttemptClose = () => {
    if (hasUnsaved) {
      const ok = window.confirm('Existem alterações não aplicadas. Fechar e descartar?')
      if (!ok) return
    }
    // Reset por sessão do painel
    setDraftInitialized(false)
    setThrRoiDirty(false); setThrItemDirty(false); setThrDivDirty(false)
    setAdvDirty({})
    setSettingsOpen(false)
  }

  return (
    <Box borderWidth="1px" borderRadius="md" bg="bg.surface">
      <Box p={5}>
        <Flex justify="space-between" align="center" mb={2}>
          <Heading size="md" mb={0}>{safeText(camera?.nome)}</Heading>
          <IconButton
            aria-label="Configurações"
            size="sm"
            variant="solid"
            colorScheme="gray"
            onClick={() => setSettingsOpen(true)}
            icon={<span style={{ fontSize: '18px', lineHeight: 1 }}>⚙️</span>}
            title="Configurações"
          />
        </Flex>
        <HStack spacing={3} mb={3}>
          <Text fontSize="sm">Status:</Text>
          <Badge colorScheme={statusColor}>{statusLabelStr}</Badge>
        </HStack>
        <HStack spacing={3} mb={4}>
          <Text fontSize="sm">Item:</Text>
          <Text fontSize="sm" color="fg.default">{safeText(modelsInfo?.item_model ? (typeof modelsInfo.item_model === 'string' ? modelsInfo.item_model.replace(/\.[^.]+$/, '') : modelsInfo.item_model) : (camera?.produto_atual || '—'))}</Text>
        </HStack>
        <HStack spacing={3} mb={4}>
          <Text fontSize="sm">Caixa:</Text>
          <Text fontSize="sm" color="fg.default">{safeText(modelsInfo?.roi_model ? (typeof modelsInfo.roi_model === 'string' ? modelsInfo.roi_model.replace(/\.[^.]+$/, '') : modelsInfo.roi_model) : '—')}</Text>
        </HStack>
        <HStack spacing={3} mb={4}>
          <Text fontSize="sm">Perfil:</Text>
          <Text fontSize="sm" color="fg.default">
            {modelsInfo?.perfil_caixa
              ? `${safeText(modelsInfo.perfil_caixa.itens_por_camada ?? '—')} × ${safeText(modelsInfo.perfil_caixa.total_camadas ?? '—')}`
              : '—'}
          </Text>
        </HStack>
        <HStack spacing={3} mb={4}>
          <Text fontSize="sm">Divisor:</Text>
          <Text fontSize="sm" color="fg.default">
            {safeText(modelsInfo?.requires_divisor === undefined ? '—' : (modelsInfo.requires_divisor ? 'Sim' : 'Não'))}
          </Text>
        </HStack>

        {/* Thresholds atuais vindos do runtime */}
        <HStack spacing={3} mb={4}>
          <Text fontSize="sm">Thresholds:</Text>
          <Text fontSize="sm" color="fg.default">
            {`ROI: ${String(typeof modelsInfo?.thresholds?.confianca_roi === 'number' ? modelsInfo.thresholds.confianca_roi.toFixed ? modelsInfo.thresholds.confianca_roi.toFixed(2) : modelsInfo.thresholds.confianca_roi : '—')}
            • Item: ${String(typeof modelsInfo?.thresholds?.confianca_item === 'number' ? modelsInfo.thresholds.confianca_item.toFixed ? modelsInfo.thresholds.confianca_item.toFixed(2) : modelsInfo.thresholds.confianca_item : '—')}
            ${requiresDivisor === false ? '' : `• Div: ${String(typeof modelsInfo?.thresholds?.confianca_divisor === 'number' ? (modelsInfo.thresholds.confianca_divisor.toFixed ? modelsInfo.thresholds.confianca_divisor.toFixed(2) : modelsInfo.thresholds.confianca_divisor) : '—')}`}`}
          </Text>
        </HStack>

        {/* Destaques de Camada/Contagem */}
        <Box mb={3}>
          <HStack spacing={4}>
            <Text fontSize="sm" fontWeight="bold">Camada:</Text>
            <Badge colorScheme="blue" variant="solid">{String(camada)}/{String(totalCamadas ?? '—')}</Badge>
            <Text fontSize="sm" fontWeight="bold">Contagem:</Text>
            <Badge colorScheme="purple" variant="solid">{String(contagem)}/{String(itensPorCamada ?? '—')}</Badge>
          </HStack>
        </Box>

        {/* Troca de produto */}
        <Box mb={4}>
          <Text fontSize="sm" color="fg.muted" mb={1}>Trocar produto</Text>
          <HStack spacing={2}>
            <select
              value={selectedProdutoId ?? ''}
              onChange={(e) => setSelectedProdutoId(e.target.value ? Number(e.target.value) : null)}
              style={{ padding: '6px 8px', fontSize: '0.875rem', borderRadius: '6px', border: '1px solid #E2E8F0', background: 'var(--chakra-colors-bg-subtle)', color: 'var(--chakra-colors-fg-default)' }}
            >
              {Array.isArray(produtos) && produtos.map((p) => (
                <option key={String(p?.id)} value={String(p?.id)}>{safeText(p?.nome)}</option>
              ))}
            </select>
            <button
              onClick={applyProduto}
              disabled={applying || !selectedProdutoId || Number(selectedProdutoId) === Number(camera?.produto_id)}
              style={{ padding: '6px 12px', fontSize: '0.875rem', borderRadius: '6px', background: '#3182CE', color: 'white', opacity: (applying || !selectedProdutoId || Number(selectedProdutoId) === Number(camera?.produto_id)) ? 0.6 : 1, cursor: (applying || !selectedProdutoId || Number(selectedProdutoId) === Number(camera?.produto_id)) ? 'not-allowed' : 'pointer', border: 'none' }}
            >
              {applying ? 'Aplicando...' : 'Aplicar'}
            </button>
          </HStack>
        </Box>

        <HStack spacing={2} mb={4}>
          <button
            onClick={startCamera}
            disabled={starting || runningNow}
            style={{ padding: '6px 10px', fontSize: '0.8rem', borderRadius: '6px', background: '#38A169', color: 'white', opacity: (starting || runningNow) ? 0.6 : 1, cursor: (starting || runningNow) ? 'not-allowed' : 'pointer', border: 'none' }}
          >
            {starting ? 'Iniciando...' : 'Iniciar'}
          </button>
          <button
          onClick={stopCamera}
          disabled={stopping || (!runningNow && !starting)}
          style={{ padding: '6px 10px', fontSize: '0.8rem', borderRadius: '6px', background: '#E53E3E', color: 'white', opacity: (stopping || (!runningNow && !starting)) ? 0.6 : 1, cursor: (stopping || (!runningNow && !starting)) ? 'not-allowed' : 'pointer', border: 'none' }}
        >
          {stopping ? 'Parando...' : 'Parar'}
        </button>
        </HStack>

        {/* Stream */}
        <Box>
          <Text fontSize="sm" color="fg.muted" mb={2}>Stream</Text>
          <Box style={{ position: 'relative' }}>
            <StreamImage
              key={`${camera.id}-${runningNow ? 'on' : 'off'}-${streamReady ? 'ready' : 'not'}`}
              cameraId={camera.id}
              height={360}
              onReady={() => setStreamReady(true)}
            />
            {overlayLabel && (
              <Box
                style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', zIndex: 2 }}
              >
                <Spinner size="md" color="white" />
                <Text style={{ color: 'white', fontWeight: 'bold', marginTop: '8px' }}>{overlayLabelStr}</Text>
              </Box>
            )}
          </Box>
        </Box>

        {/* Painel lateral custom (Settings) */}
        {settingsOpen && (
          <>
            {/* Backdrop */}
            <Box onClick={handleAttemptClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 1000 }} />
            {/* Side panel */}
            <Box role="dialog" aria-modal="true"
              onClick={(e) => e.stopPropagation()}
              style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: '360px', background: 'var(--chakra-colors-bg-surface, #1A202C)', borderLeft: '1px solid #2D3748', zIndex: 1001, display: 'flex', flexDirection: 'column' }}>
              <Box style={{ padding: '16px', borderBottom: '1px solid #2D3748' }}>
                <Heading size="sm">Configurações da Câmera</Heading>
              </Box>
              <Box style={{ padding: '16px', overflowY: 'auto', flex: 1 }}>
                <Box mb={6}>
                  <Heading size="sm" mb={3}>Thresholds (runtime)</Heading>
                  <Text fontSize="xs" color="fg.muted" mb={3}>Valores entre 0.00 e 1.00. Aplica sem reiniciar.</Text>
                  <Box mb={3} opacity={!runningNow ? 0.6 : 1}>
                    <Text fontSize="sm" mb={1}>ROI (confianca_roi)</Text>
                    <input type="text" inputMode="decimal" value={thrRoi} onFocus={() => setThrRoiDirty(true)} onChange={(e) => { setThrRoi(e.target.value); setThrRoiDirty(true) }} placeholder="0.50" disabled={!runningNow} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #E2E8F0', background: 'var(--chakra-colors-bg-subtle)', color: 'var(--chakra-colors-fg-default)' }} />
                  </Box>
                  <Box mb={3} opacity={!runningNow ? 0.6 : 1}>
                    <Text fontSize="sm" mb={1}>Item (confianca_item)</Text>
                    <input type="text" inputMode="decimal" value={thrItem} onFocus={() => setThrItemDirty(true)} onChange={(e) => { setThrItem(e.target.value); setThrItemDirty(true) }} placeholder="0.40" disabled={!runningNow} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #E2E8F0', background: 'var(--chakra-colors-bg-subtle)', color: 'var(--chakra-colors-fg-default)' }} />
                  </Box>
                  <Box mb={1} opacity={!runningNow || requiresDivisor === false ? 0.6 : 1}>
                    <Text fontSize="sm" mb={1}>Divisor (confianca_divisor)</Text>
                    <input type="text" inputMode="decimal" value={thrDiv} onFocus={() => setThrDivDirty(true)} onChange={(e) => { setThrDiv(e.target.value); setThrDivDirty(true) }} placeholder="0.25" disabled={!runningNow || requiresDivisor === false} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #E2E8F0', background: 'var(--chakra-colors-bg-subtle)', color: 'var(--chakra-colors-fg-default)' }} />
                  </Box>
                  {requiresDivisor === false && (
                    <Text fontSize="xs" color="fg.muted">Produto não exige divisor.</Text>
                  )}
                </Box>
                {/* Seção Avançado: renderiza automaticamente chaves extras numéricas/booleanas */}
                <Box mb={6}>
                  <Heading size="sm" mb={3}>Avançado</Heading>
                  {advancedKeys.length === 0 && (
                    <Text fontSize="xs" color="fg.muted">Sem parâmetros adicionais.</Text>
                  )}
                  {advancedKeys.map((k) => {
                    const curVal = allThresholds[k]
                    const isNum = typeof curVal === 'number'
                    const isBool = typeof curVal === 'boolean'
                    if (!isNum && !isBool) return null
                    if (isNum) {
                      return (
                        <Box key={k} mb={3} opacity={!runningNow ? 0.6 : 1}>
                          <Text fontSize="sm" mb={1}>{k}</Text>
                          <input
                            type="text"
                            inputMode="decimal"
                            value={String(advDraft?.[k] ?? '')}
                            onFocus={() => setAdvDirty(prev => ({ ...prev, [k]: true }))}
                            onChange={(e) => { const v = e.target.value; setAdvDraft(prev => ({ ...prev, [k]: v })); setAdvDirty(prev => ({ ...prev, [k]: true })) }}
                            placeholder={typeof curVal === 'number' ? (curVal.toFixed ? curVal.toFixed(2) : String(curVal)) : '0.00'}
                            disabled={!runningNow}
                            style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #E2E8F0', background: 'var(--chakra-colors-bg-subtle)', color: 'var(--chakra-colors-fg-default)' }}
                          />
                        </Box>
                      )
                    }
                    return (
                      <Box key={k} mb={3} opacity={!runningNow ? 0.6 : 1}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <input
                            type="checkbox"
                            checked={Boolean(advDraft?.[k])}
                            onChange={(e) => { const v = e.target.checked; setAdvDraft(prev => ({ ...prev, [k]: v })); setAdvDirty(prev => ({ ...prev, [k]: true })) }}
                            disabled={!runningNow}
                          />
                          <Text fontSize="sm">{k}</Text>
                        </label>
                      </Box>
                    )
                  })}
                </Box>
              </Box>
              {lastApplied && (
                <Box style={{ padding: '0 16px 8px 16px' }}>
                  <Text fontSize="xs" color="green.400">
                    Aplicado às {new Date(lastApplied.ts).toLocaleTimeString()} — ROI: {String(lastApplied.vals?.confianca_roi ?? '—')}, Item: {String(lastApplied.vals?.confianca_item ?? '—')}, Divisor: {String(lastApplied.vals?.confianca_divisor ?? '—')}
                  </Text>
                </Box>
              )}
              <Box style={{ padding: '12px 16px', borderTop: '1px solid #2D3748', display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <Button onClick={handleAttemptClose} variant="ghost">Fechar</Button>
                <Button colorScheme="gray" variant="outline" onClick={restoreThresholds} isDisabled={!runningNow} isLoading={restoringThr}>Restaurar padrão</Button>
                <Button colorScheme="blue" onClick={applyThresholds} isDisabled={!canApply} isLoading={savingThr}>Aplicar</Button>
              </Box>
            </Box>
          </>
        )}

        {/* Logs básicos */}
        <Box mt={4}>
          <Text fontSize="sm" color="fg.muted" mb={2}>Logs</Text>
          <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" p={3} minH="100px">
            {statusError && (
              <Text fontSize="sm" color="red.400">Erro ao obter status: {String(statusError)}</Text>
            )}
            {isLoadingStatus && (
              <Text fontSize="sm" color="fg.muted">Carregando status...</Text>
            )}
            {!isLoadingStatus && !statusError && (
              <>
                <Text fontSize="sm"><strong>Estado:</strong> {String(estado)}</Text>
                <Text fontSize="sm"><strong>Camada:</strong> {String(camada)}</Text>
                <Text fontSize="sm"><strong>Contagem:</strong> {String(contagem)}</Text>
                <Text fontSize="sm">
                  <strong>Thresholds(runtime):</strong> ROI {String(typeof modelsInfo?.thresholds?.confianca_roi === 'number' ? (modelsInfo.thresholds.confianca_roi.toFixed ? modelsInfo.thresholds.confianca_roi.toFixed(2) : modelsInfo.thresholds.confianca_roi) : '—')},
                  Item {String(typeof modelsInfo?.thresholds?.confianca_item === 'number' ? (modelsInfo.thresholds.confianca_item.toFixed ? modelsInfo.thresholds.confianca_item.toFixed(2) : modelsInfo.thresholds.confianca_item) : '—')}
                  {requiresDivisor === false ? '' : ", Div " + String(typeof modelsInfo?.thresholds?.confianca_divisor === 'number' ? (modelsInfo.thresholds.confianca_divisor.toFixed ? modelsInfo.thresholds.confianca_divisor.toFixed(2) : modelsInfo.thresholds.confianca_divisor) : '—')}
                </Text>
              </>
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  )
}

function SetorPage() {
  const { setorNome } = useParams()

  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [produtos, setProdutos] = useState([])
  const [produtosError, setProdutosError] = useState(null)

  const refreshCameras = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/cameras`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setCameras(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const run = async () => { await refreshCameras() }
    run()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    const fetchProdutos = async () => {
      try {
        const res = await fetch(`${API_URL}/produtos`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (!cancelled) setProdutos(Array.isArray(data) ? data : [])
      } catch (err) {
        if (!cancelled) setProdutosError(err.message)
      }
    }
    fetchProdutos()
    return () => { cancelled = true }
  }, [])

  const target = normalize(setorNome)
  const filtered = cameras.filter((c) => normalize(c?.setor) === target || normalize(c?.setor) === 'liquidos')
  const usedFallback = filtered.length === 0
  const displayCameras = (usedFallback ? cameras : filtered).slice(0, 2)

  return (
    <Box p={8}>
      <Heading color="fg.muted" mb={6}>{safeText(capitalizeFirstLetter(setorNome))}</Heading>

      {loading && (
        <Flex align="center" justify="center" py={12}>
          <Spinner size="lg" />
        </Flex>
      )}

      {!loading && error && (
        <Text color="red.400">Erro ao carregar câmeras: {error}</Text>
      )}

      {!loading && !error && (
        displayCameras.length > 0 ? (
          <>
            {usedFallback && (
              <Text fontSize="sm" color="fg.muted" mb={3}>
                Nenhuma câmera marcada como "Líquidos" no banco. Exibindo as 2 primeiras câmeras.
              </Text>
            )}
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
              {displayCameras.map((cam) => (
                <ErrorBoundary key={`eb-${String(cam?.id)}`}>
                  <CameraCard key={String(cam?.id)} camera={cam} produtos={produtos} onAfterChange={refreshCameras} />
                </ErrorBoundary>
              ))}
            </SimpleGrid>
          </>
        ) : (
          <Text color="fg.muted">Nenhuma câmera encontrada para este setor.</Text>
        )
      )}
    </Box>
  )
}

export default SetorPage





