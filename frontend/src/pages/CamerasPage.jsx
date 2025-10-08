import { useEffect, useState } from 'react'
import { Box, Heading, Button, Flex, Spinner, Text, HStack } from '@chakra-ui/react'
import { toaster } from '../toaster.js'

const API_URL = '/api/v1'

export default function CamerasPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [setores, setSetores] = useState([])
  const [produtos, setProdutos] = useState([])
  const [loadingAux, setLoadingAux] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({ setor_id: '', bancada: 'A', nome: '', fonte: 'ip', ip_address: '', porta: '', device_index: '' })
  const [savingEdit, setSavingEdit] = useState(false)

  const [form, setForm] = useState({
    setor_id: '',
    bancada: 'A',
    fonte: 'ip', // 'ip' | 'usb'
    ip_address: '',
    porta: '',
    device_index: '',
    produto_id: '',
    nome: '',
    ativo: true,
  })

  const fetchCameras = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/cameras`, { cache: 'no-store' })
      const data = res.ok ? await res.json() : []
      setItems(Array.isArray(data) ? data : [])
    } catch (e) {
      try {
        toaster.create({ title: 'Erro ao carregar câmeras', description: String(e?.message || e), status: 'error', duration: 4000, isClosable: true })
      } catch (_) {}
    } finally {
      setLoading(false)
    }
  }

  const startEdit = (cam) => {
    if (!cam?.id) return
    setShowForm(false)
    setEditForm({
      setor_id: String(cam?.setor_id || ''),
      bancada: String(cam?.bancada || 'A'),
      nome: cam?.nome || '',
      fonte: cam?.ip_address ? 'ip' : (cam?.device_index !== undefined && cam?.device_index !== null ? 'usb' : 'ip'),
      ip_address: cam?.ip_address || '',
      porta: (cam?.porta ?? '') === null ? '' : String(cam?.porta ?? ''),
      device_index: (cam?.device_index ?? '') === null ? '' : String(cam?.device_index ?? ''),
    })
    setEditingId(cam.id)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditForm({ setor_id: '', bancada: 'A', nome: '', fonte: 'ip', ip_address: '', porta: '', device_index: '' })
  }

  const onEditChange = (key, val) => setEditForm((p) => ({ ...p, [key]: val }))

  const saveEdit = async () => {
    try {
      if (!editingId) return
      const setorId = Number(editForm.setor_id)
      if (!Number.isFinite(setorId) || setorId <= 0) throw new Error('Informe o setor')
      const bancada = String(editForm.bancada || '').toUpperCase()
      if (!['A', 'B'].includes(bancada)) throw new Error('Bancada deve ser A ou B')
      const payload = {
        nome: (editForm.nome || '').trim() || undefined,
        setor_id: setorId,
        bancada,
      }
      // Fonte (somente do tipo atual)
      if (editForm.fonte === 'ip') {
        const ip = (editForm.ip_address || '').trim()
        if (!ip) throw new Error('Informe o IP/URL da câmera')
        payload.ip_address = ip
        if (editForm.porta !== '') {
          const p = Number(editForm.porta)
          if (!Number.isFinite(p) || p < 0) throw new Error('Porta inválida')
          payload.porta = p
        }
      } else if (editForm.fonte === 'usb') {
        const di = Number(editForm.device_index)
        if (!Number.isFinite(di) || di < 0) throw new Error('Informe o índice USB (0, 1, 2...)')
        payload.device_index = di
      }
      // Vídeo removido desta fase – manter configuração padrão da câmera
      setSavingEdit(true)
      const res = await fetch(`${API_URL}/cameras/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || res.statusText)
      try { toaster.create({ title: 'Câmera atualizada', status: 'success', duration: 2500 }) } catch {}
      setEditingId(null)
      await fetchCameras()
    } catch (e) {
      try { toaster.create({ title: 'Falha ao atualizar', description: String(e?.message || e), status: 'error', duration: 4000 }) } catch {}
    } finally {
      setSavingEdit(false)
    }
  }


  useEffect(() => { fetchCameras() }, [])

  // Carrega combos quando abrir o formulário
  useEffect(() => {
    if (!showForm) return
    let cancelled = false
    ;(async () => {
      setLoadingAux(true)
      try {
        const [resSet, resProd] = await Promise.all([
          fetch(`${API_URL}/setores`),
          fetch(`${API_URL}/produtos`),
        ])
        const setData = resSet.ok ? await resSet.json() : []
        const prodData = resProd.ok ? await resProd.json() : []
        if (!cancelled) {
          setSetores(Array.isArray(setData) ? setData : [])
          setProdutos(Array.isArray(prodData) ? prodData : [])
        }
      } catch (_) {
        try { toaster.create({ title: 'Erro ao carregar listas', status: 'error', duration: 3500 }) } catch {}
      } finally {
        if (!cancelled) setLoadingAux(false)
      }
    })()
    return () => { cancelled = true }
  }, [showForm])

  // Carrega setores on-demand quando entrar em modo edição (se ainda não carregados)
  useEffect(() => {
    if (!editingId) return
    if (Array.isArray(setores) && setores.length > 0) return
    let cancelled = false
    ;(async () => {
      try {
        const resSet = await fetch(`${API_URL}/setores`)
        const setData = resSet.ok ? await resSet.json() : []
        if (!cancelled) setSetores(Array.isArray(setData) ? setData : [])
      } catch (_) {
        /* silencioso */
      }
    })()
    return () => { cancelled = true }
  }, [editingId])

  const resetForm = () => setForm({
    setor_id: '', bancada: 'A', fonte: 'ip', ip_address: '', porta: '', device_index: '', produto_id: '', nome: '', ativo: true,
  })

  const onChange = (key, val) => setForm((p) => ({ ...p, [key]: val }))

  const submit = async () => {
    try {
      // Validações simples
      const setorId = Number(form.setor_id)
      if (!Number.isFinite(setorId) || setorId <= 0) throw new Error('Informe o setor')
      const bancada = String(form.bancada || '').toUpperCase()
      if (!['A', 'B'].includes(bancada)) throw new Error('Bancada deve ser A ou B')
      const produtoId = Number(form.produto_id)
      if (!Number.isFinite(produtoId) || produtoId <= 0) throw new Error('Selecione um produto')

      let device_index = null
      let ip_address = null
      if (form.fonte === 'ip') {
        ip_address = (form.ip_address || '').trim()
        if (!ip_address) throw new Error('Informe o IP/URL da câmera')
      } else {
        const di = Number(form.device_index)
        if (!Number.isFinite(di) || di < 0) throw new Error('Informe o índice USB (0, 1, 2...)')
        device_index = di
      }

      const payload = {
        setor_id: setorId,
        bancada,
        produto_id: produtoId,
        ip_address: ip_address || undefined,
        device_index: device_index ?? undefined,
        porta: form.porta !== '' ? Number(form.porta) : undefined,
        nome: (form.nome || '').trim() || undefined,
        ativo: !!form.ativo,
      }

      const res = await fetch(`${API_URL}/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || res.statusText)

      try { toaster.create({ title: 'Câmera criada', status: 'success', duration: 2500 }) } catch {}
      setShowForm(false)
      resetForm()
      fetchCameras()
    } catch (e) {
      try { toaster.create({ title: 'Falha ao criar', description: String(e?.message || e), status: 'error', duration: 4000 }) } catch {}
    }
  }

  const displayName = (cam) => {
    const n = (cam?.nome || '').trim()
    if (n) return n
    if (cam?.bancada) return `Bancada ${String(cam.bancada).toUpperCase()}`
    return '—'
  }
  const fonte = (cam) => {
    const ip = cam?.ip_address
    if (ip) {
      const isIPv4 = /^(?:\d{1,3}\.){3}\d{1,3}$/.test(String(ip))
      if (isIPv4 && cam?.porta) return `${ip}:${cam.porta}`
      return ip
    }
    const di = cam?.device_index
    if (di !== undefined && di !== null) return `USB ${di}`
    return '—'
  }
  const statusText = (s) => {
    const st = String(s || 'inactive').toLowerCase()
    if (st === 'active') return <Text color="green.500">Ativa</Text>
    if (st === 'offline') return <Text color="gray.500">Offline</Text>
    return <Text color="yellow.600">{st}</Text>
  }

  const removeCamera = async (cam) => {
    try {
      const camId = cam?.id
      if (!camId) return
      const name = cam?.bancada ? `Bancada ${String(cam.bancada).toUpperCase()}` : (cam?.nome || `ID ${camId}`)
      if (!window.confirm(`Remover a câmera ${name} (ID ${camId})?`)) return
      setDeletingId(camId)
      const res = await fetch(`${API_URL}/cameras/${camId}`, { method: 'DELETE' })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || res.statusText)
      try { toaster.create({ title: 'Câmera removida', status: 'success', duration: 2500 }) } catch {}
      await fetchCameras()
    } catch (e) {
      try { toaster.create({ title: 'Erro ao remover', description: String(e?.message || e), status: 'error', duration: 4000 }) } catch {}
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <Box p={8} className="cameras-page">
      <style>{`
        .cameras-page input,
        .cameras-page select,
        .cameras-page textarea {
          background-color: #fff !important;
          color: #111 !important;
          -webkit-text-fill-color: #111 !important; /* Safari */
          caret-color: #111 !important;
        }
        .cameras-page input::placeholder {
          color: #333 !important;
          opacity: 1;
        }
        .cameras-page option {
          color: #111;
          background: #fff;
        }
      `}</style>
      <Flex align="center" justify="space-between" mb={6}>
        <Heading>Câmeras</Heading>
        <HStack>
          <Button onClick={fetchCameras} colorScheme="blue" variant="outline" size="sm">Recarregar</Button>
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>{showForm ? 'Fechar' : 'Adicionar'}</Button>
        </HStack>
      </Flex>

      {showForm && (
        <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" p={4} mb={6}>
          <Flex gap={6} wrap="wrap">
            <Box minW="220px">
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>Setor</label>
              <select
                value={form.setor_id}
                onChange={(e) => onChange('setor_id', e.target.value)}
                style={{ width: '100%', padding: '8px', backgroundColor: '#fff', color: '#111' }}
              >
                <option value="">Selecione…</option>
                {setores.map((s) => (
                  <option key={String(s?.id)} value={s?.id}>{s?.nome}</option>
                ))}
              </select>
            </Box>

            <Box minW="160px">
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>Bancada</label>
              <div>
                <label style={{ marginRight: 12 }}>
                  <input type="radio" name="bancada" value="A" checked={form.bancada === 'A'} onChange={(e) => onChange('bancada', e.target.value)} /> A
                </label>
                <label>
                  <input type="radio" name="bancada" value="B" checked={form.bancada === 'B'} onChange={(e) => onChange('bancada', e.target.value)} /> B
                </label>
              </div>
            </Box>

            <Box minW="220px">
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>Fonte</label>
              <div>
                <label style={{ marginRight: 12 }}>
                  <input type="radio" name="fonte" value="ip" checked={form.fonte === 'ip'} onChange={(e) => onChange('fonte', e.target.value)} /> IP/URL
                </label>
                <label>
                  <input type="radio" name="fonte" value="usb" checked={form.fonte === 'usb'} onChange={(e) => onChange('fonte', e.target.value)} /> USB
                </label>
              </div>
            </Box>

            {form.fonte === 'ip' ? (
              <>
                <Box minW="260px">
                  <label style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>IP/URL</label>
                  <input value={form.ip_address} onChange={(e) => onChange('ip_address', e.target.value)} placeholder="10.1.1.99 ou rtsp://..." style={{ width: '100%', padding: '8px', backgroundColor: '#fff', color: '#111' }} />
                </Box>
                <Box minW="120px">
                  <label style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>Porta</label>
                  <input type="number" value={form.porta} onChange={(e) => onChange('porta', e.target.value)} placeholder="554" style={{ width: '100%', padding: '8px', backgroundColor: '#fff', color: '#111' }} />
                </Box>
              </>
            ) : (
              <Box minW="160px">
                <label style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>USB index</label>
                <input type="number" value={form.device_index} onChange={(e) => onChange('device_index', e.target.value)} placeholder="0" style={{ width: '100%', padding: '8px', backgroundColor: '#fff', color: '#111' }} />
              </Box>
            )}

            <Box minW="220px">
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>Produto</label>
              <select value={form.produto_id} onChange={(e) => onChange('produto_id', e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#fff', color: '#111' }}>
                <option value="">Selecione…</option>
                {produtos.map((p) => (
                  <option key={String(p?.id)} value={p?.id}>{p?.nome}</option>
                ))}
              </select>
            </Box>

            <Box minW="200px">
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>Nome (opcional)</label>
              <input value={form.nome} onChange={(e) => onChange('nome', e.target.value)} placeholder="ex: Bancada A" style={{ width: '100%', padding: '8px', backgroundColor: '#fff', color: '#111' }} />
            </Box>

            

            <Box minW="140px" display="flex" alignItems="center" gap={8}>
              <label style={{ fontWeight: 600 }}>Ativo</label>
              <input type="checkbox" checked={form.ativo} onChange={(e) => onChange('ativo', e.target.checked)} />
            </Box>
          </Flex>

          <HStack mt={6}>
            <Button size="sm" variant="outline" onClick={() => { resetForm(); setShowForm(false) }}>Cancelar</Button>
            <Button size="sm" colorScheme="green" onClick={submit} isDisabled={loadingAux}>{loadingAux ? 'Carregando...' : 'Salvar'}</Button>
          </HStack>
        </Box>
      )}

      {loading ? (
        <Flex align="center" justify="center" py={12}><Spinner size="lg" /></Flex>
      ) : (
        <Box borderWidth="1px" borderRadius="md" bg="bg.surface" overflowX="auto">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>ID</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>Nome</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>Setor</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>Linha</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>Fonte</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>Status</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>Produto</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((cam) => (
                <tr key={String(cam?.id)}>
                  <td style={{ padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>{cam?.id}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>
                    {editingId === cam?.id ? (
                      <input
                        value={editForm.nome}
                        onChange={(e) => onEditChange('nome', e.target.value)}
                        placeholder="Nome (opcional)"
                        style={{ width: '100%', padding: '6px', backgroundColor: '#fff', color: '#111', WebkitTextFillColor: '#111', caretColor: '#111' }}
                      />
                    ) : (
                      displayName(cam)
                    )}
                  </td>
                  <td style={{ padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>
                    {editingId === cam?.id ? (
                      <select
                        value={editForm.setor_id}
                        onChange={(e) => onEditChange('setor_id', e.target.value)}
                        style={{ width: '100%', padding: '6px', backgroundColor: '#fff', color: '#111', WebkitTextFillColor: '#111' }}
                      >
                        <option value="">Selecione…</option>
                        {setores.map((s) => (
                          <option key={String(s?.id)} value={s?.id}>{s?.nome}</option>
                        ))}
                      </select>
                    ) : (
                      cam?.setor || '—'
                    )}
                  </td>
                  <td style={{ padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>
                    {editingId === cam?.id ? (
                      <div>
                        <label style={{ marginRight: 12 }}>
                          <input type="radio" name={`bancada_${cam?.id}`} value="A" checked={editForm.bancada === 'A'} onChange={(e) => onEditChange('bancada', e.target.value)} /> A
                        </label>
                        <label>
                          <input type="radio" name={`bancada_${cam?.id}`} value="B" checked={editForm.bancada === 'B'} onChange={(e) => onEditChange('bancada', e.target.value)} /> B
                        </label>
                        <div style={{ fontSize: '12px', color: 'var(--chakra-colors-fg-muted)' }}>Linha Bancada {String(editForm.bancada || '').toUpperCase()}</div>
                      </div>
                    ) : (
                      cam?.linha_nome || '—'
                    )}
                  </td>
                  <td style={{ padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>
                    {editingId === cam?.id ? (
                      editForm.fonte === 'ip' ? (
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <input
                            value={editForm.ip_address}
                            onChange={(e) => onEditChange('ip_address', e.target.value)}
                            placeholder="rtsp://... ou 10.1.1.99"
                            style={{ width: '260px', padding: '6px', backgroundColor: '#fff', color: '#111', WebkitTextFillColor: '#111', caretColor: '#111' }}
                          />
                          <input
                            type="number"
                            value={editForm.porta}
                            onChange={(e) => onEditChange('porta', e.target.value)}
                            placeholder="554"
                            style={{ width: '90px', padding: '6px', backgroundColor: '#fff', color: '#111', WebkitTextFillColor: '#111', caretColor: '#111' }}
                          />
                        </div>
                      ) : (
                        <input
                          type="number"
                          value={editForm.device_index}
                          onChange={(e) => onEditChange('device_index', e.target.value)}
                          placeholder="0"
                          style={{ width: '100px', padding: '6px', backgroundColor: '#fff', color: '#111', WebkitTextFillColor: '#111', caretColor: '#111' }}
                        />
                      )
                    ) : (
                      fonte(cam)
                    )}
                  </td>
                  <td style={{ padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>{statusText(cam?.status)}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>{cam?.produto_atual || '—'}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid var(--chakra-colors-border-default)' }}>
                    <HStack>
                      {editingId === cam?.id ? (
                        <>
                          <Button size="xs" colorScheme="green" onClick={saveEdit} isDisabled={savingEdit}>
                            {savingEdit ? 'Salvando...' : 'Salvar'}
                          </Button>
                          <Button size="xs" variant="ghost" onClick={cancelEdit}>Cancelar</Button>
                        </>
                      ) : (
                        <>
                          <Button size="xs" variant="outline" onClick={() => startEdit(cam)}>Editar</Button>
                          <Button size="xs" variant="outline" colorScheme="red" onClick={() => removeCamera(cam)} isDisabled={deletingId === cam?.id}>
                            {deletingId === cam?.id ? 'Removendo...' : 'Remover'}
                          </Button>
                        </>
                      )}
                    </HStack>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ padding: '12px' }}><Text color="fg.muted">Nenhuma câmera cadastrada.</Text></td>
                </tr>
              )}
            </tbody>
          </table>
        </Box>
      )}
    </Box>
  )
}
