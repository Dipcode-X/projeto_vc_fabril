import { Box, Heading, Text, HStack, Badge, Button, IconButton, SimpleGrid } from '@chakra-ui/react'
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded'
import StreamImage from './StreamImage.jsx'

function safeText(val, fallback = '—') {
  if (val === null || val === undefined) return fallback
  const t = typeof val
  if (t === 'string' || t === 'number' || t === 'boolean') return String(val)
  try { return JSON.stringify(val) } catch { return fallback }
}
function stripExt(name) {
  return typeof name === 'string' ? name.replace(/\.[^.]+$/, '') : name
}

export default function CameraCard({
  cam,
  produtos,
  loadingProdutos,
  produtoValue,
  onChangeProduto,
  starting,
  stopping,
  applying,
  startCamera,
  stopCamera,
  applyProduto,
  modelsById,
  streamReady,
  onStreamReady,
  onOpenSettings,
}) {
  const runtimeItem = modelsById[cam?.id]?.item_model
  const runtimeRoi = modelsById[cam?.id]?.roi_model
  const runtimePerfil = modelsById[cam?.id]?.perfil_caixa
  const displayName = cam?.bancada ? `Bancada ${String(cam.bancada).toUpperCase()}` : safeText(cam?.nome)

  return (
    <Box borderWidth="1px" borderRadius="md" bg="bg.surface" p={4} position="relative">
      {/* Botão de engrenagem (overlay no card) */}
      <IconButton
        aria-label={`Configurações da câmera ${displayName}`}
        variant="ghost"
        size="sm"
        position="absolute"
        top="6px"
        right="6px"
        rounded="full"
        colorScheme="gray"
        _hover={{ bg: 'whiteAlpha.200' }}
        onClick={() => onOpenSettings?.(cam)}
      >
        <SettingsRoundedIcon style={{ fontSize: 20 }} />
      </IconButton>

      {/* Cabeçalho */}
      <Heading size="sm" mb={2}>{displayName}</Heading>
      <HStack spacing={2} mb={4}>
        <Text fontSize="sm">Status:</Text>
        <Badge colorScheme={['active','online','running',true].includes((cam?.status||'').toString().toLowerCase()) ? 'green' : 'red'}>
          {safeText(cam?.status)}
        </Badge>
      </HStack>

      {/* Topo: Dados (esquerda) e Controles (direita) */}
      <SimpleGrid columns={{ base: 1, lg: 2 }} columnGap={8} rowGap={4}>
        {/* Dados */}
        <Box borderWidth="1px" borderRadius="md" p={3} bg="bg.subtle" minH="160px">
          <Heading size="xs" mb={2}>Dados</Heading>
          <Box fontSize="sm" color="fg.muted" display="grid" rowGap={3}>
            <Text>
              {(() => {
                const name = stripExt(runtimeItem || cam?.produto_atual || '—')
                return <>Item: {safeText(name)}</>
              })()}
            </Text>
            <Text>
              {(() => {
                const name = stripExt(runtimeRoi || '—')
                return <>Caixa: {safeText(name)}</>
              })()}
            </Text>
            <Text>
              {(() => {
                if (runtimePerfil && (runtimePerfil?.itens_por_camada || runtimePerfil?.total_camadas)) {
                  return <>Perfil: {safeText(runtimePerfil?.itens_por_camada)} × {safeText(runtimePerfil?.total_camadas)}</>
                }
                return <>Perfil: —</>
              })()}
            </Text>
          </Box>
        </Box>

        {/* Controles */}
        <Box borderWidth="1px" borderRadius="md" p={3} bg="bg.subtle" minH="160px">
          <Heading size="xs" mb={2}>Controles</Heading>
          <Box>
            <Text fontSize="xs" color="fg.muted" mb={1}>Selecionar item</Text>
            <select
              disabled={loadingProdutos}
              value={produtoValue}
              onChange={(e) => onChangeProduto?.(cam?.id, e.target.value)}
              style={{ padding: '6px 8px', fontSize: '0.875rem', borderRadius: '6px', border: '1px solid #E2E8F0', background: 'var(--chakra-colors-bg-subtle)', color: 'var(--chakra-colors-fg-default)', width: '100%' }}
            >
              <option value="">{loadingProdutos ? 'Carregando...' : 'Selecione...'}</option>
              {Array.isArray(produtos) && produtos.map((p) => (
                <option key={String(p?.id)} value={String(p?.id)}>{safeText(p?.nome)}</option>
              ))}
            </select>

            {/* Barra de ações centralizada */}
            <HStack spacing={2} flexWrap="wrap" mt={4} justifyContent="space-evenly" alignItems="center" w="100%">
              <Button size="xs" h="28px" fontSize="xs" colorScheme="green" onClick={() => startCamera?.(cam?.id)} isLoading={!!starting} isDisabled={Boolean(cam?.__placeholder)} minW="auto" px={2} rounded="sm">
                Iniciar
              </Button>
              <Button size="xs" h="28px" fontSize="xs" colorScheme="red" onClick={() => stopCamera?.(cam?.id)} isLoading={!!stopping} isDisabled={Boolean(cam?.__placeholder)} minW="auto" px={2} rounded="sm">
                Parar
              </Button>
              <Button size="xs" h="28px" fontSize="xs" colorScheme="blue" onClick={() => applyProduto?.(cam?.id)} isLoading={!!applying} isDisabled={Boolean(cam?.__placeholder)} minW="auto" px={2} rounded="sm">
                Aplicar
              </Button>
            </HStack>
          </Box>
        </Box>
      </SimpleGrid>

      {/* Stream grande abaixo */}
      <Box mt={4} borderWidth="1px" borderRadius="md" p={6} bg="bg.subtle" minH="300px">
        <Heading size="xs" mb={2}>Visualização</Heading>
        {cam.__placeholder ? (
          <Box borderWidth="1px" borderRadius="sm" borderStyle="dashed" h="380px" display="flex" alignItems="center" justifyContent="center" color="fg.muted">
            <Text fontSize="sm">Stream (grande)</Text>
          </Box>
        ) : (
          (() => {
            const shouldShowStream = starting || streamReady
            if (!shouldShowStream) {
              return (
                <Box borderWidth="1px" borderRadius="sm" borderStyle="dashed" h="380px" display="flex" alignItems="center" justifyContent="center" color="fg.muted">
                  <Text fontSize="sm">Sem stream disponível</Text>
                </Box>
              )
            }
            return (
              <StreamImage
                cameraId={cam.id}
                height={380}
                mode="mjpeg"
                retryBaseMs={800}   // mude aqui se quiser
                retryMaxMs={15000}   // mude aqui se quiser
                firstTryAfterPreamble={false}
                onReady={() => onStreamReady?.(cam.id)}
              />
            )
          })()
        )}
      </Box>

      {/* Logs */}
      <Box borderWidth="1px" borderRadius="md" p={6} bg="bg.subtle" mt={4}>
        <Heading size="xs" mb={2}>Logs</Heading>
        <Text fontSize="xs" color="fg.muted">Eventos e mensagens serão mostrados aqui.</Text>
      </Box>
    </Box>
  )
}
