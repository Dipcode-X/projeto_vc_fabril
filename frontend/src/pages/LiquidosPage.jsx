import { useEffect, useState } from 'react'
import { Box, Heading, Text, SimpleGrid, Spinner, Flex } from '@chakra-ui/react'
import { toaster } from '../toaster.js'
import SettingsDialog from '../components/liquidos/SettingsDialog.jsx'
import CameraCard from '../components/liquidos/CameraCard.jsx'

const API_URL = '/api/v1'

function normalize(str) {
  return (str || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

function safeText(val, fallback = '—') {
  if (val === null || val === undefined) return fallback
  const t = typeof val
  if (t === 'string' || t === 'number' || t === 'boolean') return String(val)
  try {
    return JSON.stringify(val)
  } catch {
    return fallback
  }
}

// Formata rótulo do produto no seletor com dados vindos do SQLite (/produtos)
function stripExt(name) {
  return typeof name === 'string' ? name.replace(/\.[^.]+$/, '') : name
}
function formatProdutoLabel(p) {
  if (!p) return '—'
  const nome = safeText(p?.nome)
  // perfil direto nas colunas (quando disponível)
  const ipc = p?.itens_por_camada
  const maxc = p?.max_camadas
  // modelos no config_json
  const cfg = p?.config_json || {}
  const itemModel = stripExt(cfg?.item_model)
  const roiModel = stripExt(cfg?.roi_model)
  const parts = [nome]
  if (ipc && maxc) parts.push(`Perfil: ${ipc}×${maxc}`)
  if (itemModel) parts.push(`Item: ${itemModel}`)
  if (roiModel) parts.push(`Caixa: ${roiModel}`)
  return parts.join(' — ')
}

// StreamImage foi modularizado em ../components/liquidos/StreamImage.jsx

export default function LiquidosPage() {
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [modelsById, setModelsById] = useState({})
  const [produtos, setProdutos] = useState([])
  const [loadingProdutos, setLoadingProdutos] = useState(false)
  const [produtoSelById, setProdutoSelById] = useState({})
  const [startingById, setStartingById] = useState({})
  const [stoppingById, setStoppingById] = useState({})
  const [applyingById, setApplyingById] = useState({})
  const [streamReadyById, setStreamReadyById] = useState({})
  const [advancedById, setAdvancedById] = useState({})

  // Modal de Configurações (por câmera)
  const [settingsCam, setSettingsCam] = useState(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  // Thresholds por câmera + rascunho do formulário
  const [thresholdsById, setThresholdsById] = useState({})
  const [draftThresholds, setDraftThresholds] = useState({ item: 0.5, divisor: 0.5, roi: 0.5 })
  const clamp01 = (n) => Math.max(0, Math.min(1, Number.isFinite(n) ? n : 0))

  useEffect(() => {
    if (!dialogOpen) return
    const id = settingsCam?.id
    // Base local salva (snapshot) e runtime atual no momento da abertura
    const baseLocal = (id != null && thresholdsById[id]) ? thresholdsById[id] : { item: 0.5, divisor: 0.5, roi: 0.5 }
    const thr = (id != null) ? (modelsById[id]?.thresholds || {}) : {}
    const base = {
      item: clamp01(thr.confianca_item ?? baseLocal.item),
      divisor: clamp01(thr.confianca_divisor ?? baseLocal.divisor),
      roi: clamp01(thr.confianca_roi ?? baseLocal.roi),
    }
    setDraftThresholds(base)
  }, [dialogOpen, settingsCam])

  const handleSaveThresholds = async () => {
    const id = settingsCam?.id
    if (id == null) {
      setDialogOpen(false)
      return
    }
    // Monta payload clampado 0..1
    const payload = {
      roi: clamp01(draftThresholds.roi),
      item: clamp01(draftThresholds.item),
      divisor: clamp01(draftThresholds.divisor),
    }
    try {
      const res = await fetch(`${API_URL}/cameras/${id}/thresholds`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confianca_roi: payload.roi,
          confianca_item: payload.item,
          confianca_divisor: payload.divisor,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || res.statusText)

      // Atualiza cache local para o formulário e reflete no card
      setThresholdsById((prev) => ({ ...prev, [id]: { ...payload } }))
      // Atualiza imediatamente os thresholds mostrados no card com o que o backend reportou em runtime
      if (data && data.runtime_thresholds) {
        setModelsById((prev) => ({
          ...prev,
          [id]: {
            ...(prev?.[id] || {}),
            thresholds: { ...data.runtime_thresholds },
          },
        }))
      }
      await refetchModelsFor(id)

      try {
        toaster.create({
          title: 'Thresholds aplicados',
          description: `Item: ${payload.item.toFixed(2)} | Divisor: ${payload.divisor.toFixed(2)} | ROI: ${payload.roi.toFixed(2)}`,
          status: 'success',
          duration: 2500,
          isClosable: true,
        })
      } catch (_) {}
    } catch (e) {
      try {
        toaster.create({ title: 'Falha ao aplicar thresholds', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
      } catch (_) {}
    } finally {
      setDialogOpen(false)
    }
  }

  // Carrega câmeras
  useEffect(() => {
    let cancelled = false
    const fetchCameras = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API_URL}/cameras`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (!cancelled) setCameras(Array.isArray(data) ? data : [])
      } catch (e) {
        if (!cancelled) {
          setError(e.message)
          toaster.create({
            title: 'Erro ao carregar câmeras',
            description: String(e?.message || e),
            status: 'error',
            duration: 4000,
            isClosable: true,
          })
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchCameras()
    return () => {
      cancelled = true
    }
  }, [])

  // Carrega produtos
  useEffect(() => {
    let cancelled = false
    const fetchProdutos = async () => {
      setLoadingProdutos(true)
      try {
        const res = await fetch(`${API_URL}/produtos`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (!cancelled) setProdutos(Array.isArray(data) ? data : [])
      } catch (e) {
        if (!cancelled)
          toaster.create({
            title: 'Erro ao carregar produtos',
            description: String(e?.message || e),
            status: 'error',
            duration: 4000,
            isClosable: true,
          })
      } finally {
        if (!cancelled) setLoadingProdutos(false)
      }
    }
    fetchProdutos()
    return () => {
      cancelled = true
    }
  }, [])

  const liquidos = cameras.filter((c) => normalize(c?.setor) === 'liquidos')
  const display = liquidos.length > 0 ? liquidos : cameras
  const items = display.length > 0 ? display : [{ id: 'placeholder-1', nome: 'Câmera (exemplo)', status: 'offline', __placeholder: true }]

  // Se status reportar offline, garanta que o overlay de starting seja removido
  useEffect(() => {
    if (!Array.isArray(cameras) || cameras.length === 0) return
    setStartingById((prev) => {
      let changed = false
      const next = { ...prev }
      for (const cam of cameras) {
        const id = cam?.id
        if (!Number.isFinite(Number(id))) continue
        const statusStr = (cam?.status || '').toString().toLowerCase()
        const running = ['active', 'online', 'running', true].includes(statusStr)
        if (!running && next[id]) {
          next[id] = false
          changed = true
        }
      }
      return changed ? next : prev
    })
  }, [cameras])

  // Busca de modelos por câmera (para Item/Caixa/Perfil)
  useEffect(() => {
    let cancelled = false
    const realIds = display.filter((c) => !c?.__placeholder && c?.id != null).map((c) => c.id)
    const missing = realIds.filter((id) => modelsById[id] === undefined)
    if (missing.length === 0) return
    ;(async () => {
      try {
        const results = await Promise.all(
          missing.map(async (id) => {
            try {
              const res = await fetch(`${API_URL}/cameras/${id}/models`)
              const data = res.ok ? await res.json() : null
              return { id, data }
            } catch (_) {
              return { id, data: null }
            }
          }),
        )
        if (!cancelled) {
          setModelsById((prev) => {
            const next = { ...prev }
            for (const { id, data } of results) next[id] = data
            return next
          })
        }
      } catch (_) {}
    })()
    return () => {
      cancelled = true
    }
  }, [display, modelsById])

  // Utilitário para refetch rápido após ações
  const refetchCameras = async () => {
    try {
      const res = await fetch(`${API_URL}/cameras`)
      const data = res.ok ? await res.json() : []
      setCameras(Array.isArray(data) ? data : [])
    } catch (_) {}
  }

  // Recarrega modelos/thresholds/perfil de uma câmera específica
  const refetchModelsFor = async (camId) => {
    try {
      const res = await fetch(`${API_URL}/cameras/${camId}/models`, { cache: 'no-store' })
      const data = res.ok ? await res.json() : null
      if (data) setModelsById((prev) => ({ ...prev, [camId]: data }))
    } catch (_) {}
  }

  // Nome exibido consistente (prioriza Bancada X)
  const getDisplayName = (cam) => {
    try {
      if (cam?.bancada) return `Bancada ${String(cam.bancada).toUpperCase()}`
      return safeText(cam?.nome)
    } catch (_) {
      return safeText(cam?.nome)
    }
  }

  // Handlers por câmera
  const onChangeProduto = (camId, value) => {
    setProdutoSelById((prev) => ({ ...prev, [camId]: value ? Number(value) : null }))
  }
  const getProdutoValue = (cam) => {
    if (!cam) return ''
    const sel = produtoSelById[cam.id]
    if (sel != null) return sel
    if (cam.__placeholder) return ''
    return cam?.produto_id ?? ''
  }
  const getSelectedProduto = (cam) => {
    try {
      const id = getProdutoValue(cam)
      if (!id) return null
      const list = Array.isArray(produtos) ? produtos : []
      return list.find((p) => Number(p?.id) === Number(id)) || null
    } catch (_) {
      return null
    }
  }

  const startCamera = async (camId) => {
    if (!Number.isFinite(Number(camId))) {
      toaster.create({ title: 'Câmera inválida', description: 'Selecione uma câmera real para iniciar.', status: 'info', duration: 2500, isClosable: true })
      return
    }
    setStartingById((p) => ({ ...p, [camId]: true }))
    setStreamReadyById((p) => ({ ...p, [camId]: false }))
    try {
      const res = await fetch(`${API_URL}/cameras/${camId}/start`, { method: 'POST' })
      await res.json().catch(() => {})
      if (!res.ok) throw new Error(res.statusText)
    } catch (e) {
      toaster.create({ title: 'Falha ao iniciar câmera', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
      setStartingById((p) => ({ ...p, [camId]: false }))
    }
    refetchCameras()
  }

  const stopCamera = async (camId) => {
    if (!Number.isFinite(Number(camId))) {
      toaster.create({ title: 'Câmera inválida', description: 'Selecione uma câmera real para parar.', status: 'info', duration: 2500, isClosable: true })
      return
    }
    setStoppingById((p) => ({ ...p, [camId]: true }))
    try {
      const res = await fetch(`${API_URL}/cameras/${camId}/stop`, { method: 'POST' })
      await res.json().catch(() => {})
      if (!res.ok) throw new Error(res.statusText)
      toaster.create({ title: 'Câmera parada', status: 'success', duration: 2500, isClosable: true })
    } catch (e) {
      toaster.create({ title: 'Falha ao parar', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
    } finally {
      setStoppingById((p) => ({ ...p, [camId]: false }))
      setStartingById((p) => ({ ...p, [camId]: false }))
      setStreamReadyById((p) => ({ ...p, [camId]: false }))
      refetchCameras()
    }
  }

  const applyProduto = async (camId) => {
    const current = cameras.find((c) => c?.id === camId)
    const selected = produtoSelById[camId] ?? current?.produto_id
    if (!selected) {
      toaster.create({ title: 'Selecione um item', status: 'info', duration: 2500, isClosable: true })
      return
    }
    setApplyingById((p) => ({ ...p, [camId]: true }))
    try {
      const res = await fetch(`${API_URL}/cameras/${camId}/produto`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ produto_id: Number(selected) }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || res.statusText)
      toaster.create({ title: 'Produto aplicado', description: String(data?.produto_nome || ''), status: 'success', duration: 3000, isClosable: true })
      // Após aplicar o produto, recarregar modelos/thresholds/perfil para refletir no card
      await refetchModelsFor(camId)
    } catch (e) {
      toaster.create({ title: 'Falha ao aplicar produto', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
    } finally {
      setApplyingById((p) => ({ ...p, [camId]: false }))
      refetchCameras()
      // E garantir uma atualização posterior dos modelos
      refetchModelsFor(camId)
    }
  }

  return (
    <Box p={8}>
      {/* Cabeçalho da página (sem engrenagem global) */}
      <Flex align="center" justify="flex-start" mb={6}>
        <Heading color="fg.muted">Setor: Líquidos</Heading>
      </Flex>

      {loading && (
        <Flex align="center" justify="center" py={12}>
          <Spinner size="lg" />
        </Flex>
      )}

      {!loading && error && <Text color="red.400">Erro ao carregar câmeras: {error}</Text>}

      {!loading && !error && (
        <>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
            {items.map((cam) => (
              <CameraCard
                key={String(cam?.id)}
                cam={cam}
                produtos={produtos}
                loadingProdutos={loadingProdutos}
                produtoValue={String(getProdutoValue(cam) ?? '')}
                onChangeProduto={onChangeProduto}
                starting={!!startingById[cam?.id]}
                stopping={!!stoppingById[cam?.id]}
                applying={!!applyingById[cam?.id]}
                startCamera={startCamera}
                stopCamera={stopCamera}
                applyProduto={applyProduto}
                modelsById={modelsById}
                streamReady={!!streamReadyById[cam?.id]}
                onStreamReady={(id) => {
                  setStreamReadyById((p) => ({ ...p, [id]: true }))
                  setStartingById((p) => ({ ...p, [id]: false }))
                  // Quando o stream estiver pronto, refetch dos modelos para refletir runtime/perfil
                  refetchModelsFor(id)
                }}
                onOpenSettings={(c) => { setSettingsCam(c); setDialogOpen(true) }}
              />
            ))}
          </SimpleGrid>

          {display.length === 0 && (
            <Text mt={4} color="fg.muted">
              Exibindo layout de exemplo. Adicione câmeras ao setor "Líquidos" para ver dados reais.
            </Text>
          )}
        </>
      )}

      {/* Dialog extraído para componente dedicado */}
      <SettingsDialog
        open={dialogOpen}
        onOpenChange={(e) => setDialogOpen(e.open)}
        camName={getDisplayName(settingsCam) || safeText(settingsCam?.nome)}
        values={draftThresholds}
        onChange={setDraftThresholds}
        onCancel={() => setDialogOpen(false)}
        onSave={handleSaveThresholds}
        advancedValues={settingsCam?.id != null ? advancedById[settingsCam.id] : undefined}
        onChangeAdvanced={(adv) => {
          const id = settingsCam?.id
          if (id == null) return
          setAdvancedById((p) => ({ ...p, [id]: adv }))
          try { toaster.create({ title: 'Avançado aplicado', status: 'success', duration: 2000 }) } catch (_) {}
        }}
      />
    </Box>
  )
}
