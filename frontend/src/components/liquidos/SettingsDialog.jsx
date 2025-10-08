import { useState, useEffect } from 'react'
import { Dialog, Drawer, Portal, VStack, Box, Text, Input, Button, Switch } from '@chakra-ui/react'

export default function SettingsDialog({
  open,
  onOpenChange,
  camName,
  values,
  onChange,
  onCancel,
  onSave,
  advancedValues,
  onChangeAdvanced,
}) {
  const handleNum = (key) => (e) => {
    // Aceita vírgula como separador decimal (pt-BR)
    const raw = String(e.target.value || '').replace(',', '.')
    const v = parseFloat(raw)
    const next = Number.isFinite(v) ? v : 0
    onChange?.({ ...values, [key]: clamp01(next) })
  }

  const clamp01 = (n) => Math.max(0, Math.min(1, Number.isFinite(n) ? n : 0))

  // Advanced panel state (local for now)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const defaultAdvanced = {
    tamanho_buffer_estabilizacao: 5,
    percentual_itens_novos_minimo: 0.7,
    distancia_minima_item_novo: 50,
    tempo_limite_caixa_ausente: 30.0,
    itens_minimos_camada_2_estabelecida: 5,
    tempo_carencia_divisor_ausente: 3.0,
    tempo_carencia_contagem_baixa: 2.0,
    salto_suspeito_minimo: 3,
    tempo_carencia_salto: 2.0,
    tempo_maximo_salto: 2.0,
    percentual_itens_novos_salto: 0.7,
    tempo_divisor_estavel_minimo: 3.0,
    tempo_maximo_instabilidade_divisor: 2.0,
    usar_validacao_divisor_salto: true,
  }
  const [adv, setAdv] = useState(advancedValues || defaultAdvanced)
  const setAdvNum = (key) => (e) => {
    const v = parseFloat(e.target.value)
    setAdv((p) => ({ ...p, [key]: Number.isFinite(v) ? v : 0 }))
  }
  const setAdvInt = (key) => (e) => {
    const v = parseInt(e.target.value, 10)
    setAdv((p) => ({ ...p, [key]: Number.isFinite(v) ? v : 0 }))
  }

  // Sync from parent when dialog opens or values change
  useEffect(() => {
    if (open) {
      setAdv(advancedValues || defaultAdvanced)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, advancedValues?.tamanho_buffer_estabilizacao])

  return (
    <>
      <Dialog.Root open={open} onOpenChange={onOpenChange}>
        <Portal>
          <Dialog.Backdrop />
          <Dialog.Positioner>
            <Dialog.Content>
              <Dialog.Header>
                <Dialog.Title>Configurações — {camName || 'Líquidos'}</Dialog.Title>
              </Dialog.Header>
              <Dialog.Body>
                <VStack align="stretch" spacing={4}>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Threshold de confiança — Item</Text>
                    <Input type="number" inputMode="decimal" step="0.01" min="0" max="1" value={String(values.item)} onChange={handleNum('item')} />
                    <Text fontSize="xs" color="fg.muted" mt={1}>Intervalo permitido: 0.00 a 1.00</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Threshold de confiança — Divisor</Text>
                    <Input type="number" inputMode="decimal" step="0.01" min="0" max="1" value={String(values.divisor)} onChange={handleNum('divisor')} />
                    <Text fontSize="xs" color="fg.muted" mt={1}>Intervalo permitido: 0.00 a 1.00</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Threshold de confiança — ROI</Text>
                    <Input type="number" inputMode="decimal" step="0.01" min="0" max="1" value={String(values.roi)} onChange={handleNum('roi')} />
                    <Text fontSize="xs" color="fg.muted" mt={1}>Intervalo permitido: 0.00 a 1.00</Text>
                  </Box>
                  <Box display="flex" justifyContent="flex-end" gap={3} pt={2}>
                    <Button variant="outline" onClick={() => setAdvancedOpen(true)}>Avançado</Button>
                    <Button variant="ghost" onClick={onCancel}>Cancelar</Button>
                    <Button colorScheme="blue" onClick={onSave} isDisabled={!camName}>Salvar</Button>
                  </Box>
                </VStack>
              </Dialog.Body>
              <Dialog.CloseTrigger />
            </Dialog.Content>
          </Dialog.Positioner>
        </Portal>
      </Dialog.Root>

      {/* Advanced side drawer */}
      <Drawer.Root open={advancedOpen} onOpenChange={(e) => setAdvancedOpen(e.open)} placement="end">
        <Portal>
          <Drawer.Backdrop />
          <Drawer.Positioner>
            <Drawer.Content style={{ width: '420px', maxWidth: '90vw' }}>
              <Drawer.Header>
                <Drawer.Title>Parâmetros avançados</Drawer.Title>
              </Drawer.Header>
              <Drawer.Body>
                <VStack align="stretch" spacing={4}>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Tamanho buffer de estabilização</Text>
                    <Input type="number" inputMode="numeric" step="1" min="0" value={String(adv.tamanho_buffer_estabilizacao)} onChange={setAdvInt('tamanho_buffer_estabilizacao')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Percentual itens novos mínimo</Text>
                    <Input type="number" inputMode="decimal" step="0.01" min="0" max="1" value={String(adv.percentual_itens_novos_minimo)} onChange={setAdvNum('percentual_itens_novos_minimo')} />
                    <Text fontSize="xs" color="fg.muted" mt={1}>Intervalo: 0.00 a 1.00</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Distância mínima item novo</Text>
                    <Input type="number" inputMode="numeric" step="1" min="0" value={String(adv.distancia_minima_item_novo)} onChange={setAdvInt('distancia_minima_item_novo')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Tempo limite caixa ausente (s)</Text>
                    <Input type="number" inputMode="decimal" step="0.1" min="0" value={String(adv.tempo_limite_caixa_ausente)} onChange={setAdvNum('tempo_limite_caixa_ausente')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Itens mínimos p/ camada 2</Text>
                    <Input type="number" inputMode="numeric" step="1" min="0" value={String(adv.itens_minimos_camada_2_estabelecida)} onChange={setAdvInt('itens_minimos_camada_2_estabelecida')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Carência divisor ausente (s)</Text>
                    <Input type="number" inputMode="decimal" step="0.1" min="0" value={String(adv.tempo_carencia_divisor_ausente)} onChange={setAdvNum('tempo_carencia_divisor_ausente')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Carência contagem baixa (s)</Text>
                    <Input type="number" inputMode="decimal" step="0.1" min="0" value={String(adv.tempo_carencia_contagem_baixa)} onChange={setAdvNum('tempo_carencia_contagem_baixa')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Salto suspeito mínimo</Text>
                    <Input type="number" inputMode="numeric" step="1" min="0" value={String(adv.salto_suspeito_minimo)} onChange={setAdvInt('salto_suspeito_minimo')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Carência de salto (s)</Text>
                    <Input type="number" inputMode="decimal" step="0.1" min="0" value={String(adv.tempo_carencia_salto)} onChange={setAdvNum('tempo_carencia_salto')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Tempo máximo de salto (s)</Text>
                    <Input type="number" inputMode="decimal" step="0.1" min="0" value={String(adv.tempo_maximo_salto)} onChange={setAdvNum('tempo_maximo_salto')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Percentual itens novos (salto)</Text>
                    <Input type="number" inputMode="decimal" step="0.01" min="0" max="1" value={String(adv.percentual_itens_novos_salto)} onChange={setAdvNum('percentual_itens_novos_salto')} />
                    <Text fontSize="xs" color="fg.muted" mt={1}>Intervalo: 0.00 a 1.00</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Divisor estável mínimo (s)</Text>
                    <Input type="number" inputMode="decimal" step="0.1" min="0" value={String(adv.tempo_divisor_estavel_minimo)} onChange={setAdvNum('tempo_divisor_estavel_minimo')} />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={1}>Máx. instabilidade do divisor (s)</Text>
                    <Input type="number" inputMode="decimal" step="0.1" min="0" value={String(adv.tempo_maximo_instabilidade_divisor)} onChange={setAdvNum('tempo_maximo_instabilidade_divisor')} />
                  </Box>
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Text fontSize="sm" fontWeight="medium">Usar validação por divisor no salto</Text>
                    <Switch.Root checked={!!adv.usar_validacao_divisor_salto} onCheckedChange={(e) => setAdv((p) => ({ ...p, usar_validacao_divisor_salto: e.checked }))}>
                      <Switch.HiddenInput />
                      <Switch.Control>
                        <Switch.Thumb />
                      </Switch.Control>
                      <Switch.Label />
                    </Switch.Root>
                  </Box>
                  <Box display="flex" justifyContent="flex-end" gap={3} pt={2}>
                    <Button variant="ghost" onClick={() => setAdvancedOpen(false)}>Fechar</Button>
                    <Button colorScheme="blue" onClick={() => { onChangeAdvanced?.(adv); setAdvancedOpen(false) }}>Aplicar</Button>
                  </Box>
                </VStack>
              </Drawer.Body>
              <Drawer.CloseTrigger />
            </Drawer.Content>
          </Drawer.Positioner>
        </Portal>
      </Drawer.Root>
    </>
  )
}
