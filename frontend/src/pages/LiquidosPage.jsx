// frontend/src/pages/LiquidosPage.jsx
import { useEffect, useState } from 'react'
import {
  Box,
  Container,
  Heading,
  Text,
  SimpleGrid,
  Grid,
  GridItem,
  Flex,
  Badge,
  DataList,
  Select,
  Button,
  HStack,
  Portal,
  Center,
  Spinner,
  createListCollection,
} from '@chakra-ui/react'
import CameraStream from '../components/CameraStream.jsx'
import { startCamera, stopCamera, getCameraStatus } from '../Lib/api.js'

const produtosCollection = createListCollection({
  items: [
    { label: 'ac_madepil', value: 'ac_madepil', categoria: 'Líquidos' },
    { label: 'glifosato_dipil_480', value: 'glifosato_dipil_480', categoria: 'Líquidos' },
  ],
})

// Agrupamento sem dependências externas
const categorias = Object.entries(
  produtosCollection.items.reduce((acc, item) => {
    const key = item.categoria || 'Produtos'
    if (!acc[key]) acc[key] = []
    acc[key].push(item)
    return acc
  }, {}),
)

export default function LiquidosPage() {
  // Usaremos a webcam do Mac como id 0
  const CAMERA_ID_A = 0

  // Estado Linha A
  const [runningA, setRunningA] = useState(false)
  const [statusA, setStatusA] = useState(null)
  const [loadingStartA, setLoadingStartA] = useState(false)
  const [loadingStopA, setLoadingStopA] = useState(false)
  const [bootingA, setBootingA] = useState(false) // spinner enquanto aguardamos running=true

  async function fetchStatusA() {
    try {
      const s = await getCameraStatus(CAMERA_ID_A)
      setStatusA(s)
      setRunningA(Boolean(s?.running))
      return s
    } catch (err) {
      console.error('Erro ao obter status da câmera A:', err)
      setRunningA(false)
      return null
    }
  }

  // util: espera até running=true com timeout curto
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
  async function waitForRunningA({ tries = 15, interval = 200 } = {}) {
    for (let i = 0; i < tries; i++) {
      const s = await fetchStatusA()
      if (s?.running) return s
      await sleep(interval)
    }
    return null
  }

  useEffect(() => {
    fetchStatusA()
  }, [])

  async function handleStartA() {
    try {
      setLoadingStartA(true)
      setBootingA(true)
      await startCamera(CAMERA_ID_A)
      // Aguarda running=true para evitar necessidade de 2 cliques
      await waitForRunningA()
    } catch (err) {
      console.error('Falha ao iniciar câmera A:', err)
    } finally {
      setLoadingStartA(false)
      setBootingA(false)
    }
  }

  async function handleStopA() {
    try {
      setLoadingStopA(true)
      await stopCamera(CAMERA_ID_A)
      await fetchStatusA()
    } catch (err) {
      console.error('Falha ao parar câmera A:', err)
    } finally {
      setLoadingStopA(false)
      setBootingA(false)
    }
  }

  return (
    <Box flex="1" overflowY="auto">
      <Container maxW="container.xl" py={6}>
        {/* Topbar simples (placeholder) */}
        <Heading size="lg" mb={4}>SIAC Industrial • Líquidos</Heading>

        {/* KPIs (placeholder) */}
        <SimpleGrid columns={{ base: 1, md: 4 }} spacing={4} mb={6}>
          {['KPI 1', 'KPI 2', 'KPI 3', 'KPI 4'].map((label) => (
            <Box key={label} borderWidth="1px" borderRadius="md" bg="bg.surface" p={4}>
              <Text fontSize="sm" color="fg.muted">{label}</Text>
              <Box h="28px" />
            </Box>
          ))}
        </SimpleGrid>

        {/* 2 colunas principais: Linha A / Linha B */}
        <Grid templateColumns={{ base: '1fr', xl: '1fr 1fr' }} gap={6}>
          {/* Linha A */}
          <GridItem>
            <Box borderWidth="1px" borderRadius="md" bg="bg.surface" p={4}>
              <Heading size="md" mb={4}>Linha A</Heading>

              {/* Esquerda: DataList | Direita: Select (v3) + botões */}
              <Flex direction={{ base: 'column', md: 'row' }} gap={6} mb={4}>
                {/* DataList */}
                <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" p={3} flex="1">
                  <DataList.Root orientation="horizontal" divideY="1px">
                    <DataList.Item>
                      <DataList.ItemLabel>Status</DataList.ItemLabel>
                      <DataList.ItemValue>
                        <Badge colorScheme={runningA ? 'green' : 'gray'}>
                          {runningA ? 'Online' : 'Offline'}
                        </Badge>
                      </DataList.ItemValue>
                    </DataList.Item>
                    <DataList.Item>
                      <DataList.ItemLabel>Item</DataList.ItemLabel>
                      <DataList.ItemValue>{statusA?.product_name ?? '—'}</DataList.ItemValue>
                    </DataList.Item>
                    <DataList.Item>
                      <DataList.ItemLabel>Perfil</DataList.ItemLabel>
                      <DataList.ItemValue>6 × 1</DataList.ItemValue>
                    </DataList.Item>
                  </DataList.Root>
                </Box>

                {/* Select v3 + botões */}
                <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" p={3} flex="1">
                  <Select.Root collection={produtosCollection} size="sm" width="100%">
                    <Select.HiddenSelect />
                    <Select.Label>Trocar produto</Select.Label>
                    <Select.Control>
                      <Select.Trigger>
                        <Select.ValueText placeholder="Selecione um produto" />
                      </Select.Trigger>
                      <Select.IndicatorGroup>
                        <Select.Indicator />
                      </Select.IndicatorGroup>
                    </Select.Control>
                    <Portal>
                      <Select.Positioner>
                        <Select.Content>
                          {categorias.map(([categoria, items]) => (
                            <Select.ItemGroup key={categoria}>
                              <Select.ItemGroupLabel>{categoria}</Select.ItemGroupLabel>
                              {items.map((item) => (
                                <Select.Item item={item} key={item.value}>
                                  {item.label}
                                  <Select.ItemIndicator />
                                </Select.Item>
                              ))}
                            </Select.ItemGroup>
                          ))}
                        </Select.Content>
                      </Select.Positioner>
                    </Portal>
                  </Select.Root>

                  <HStack spacing={2} mt={3}>
                    <Button
                      size="sm"
                      colorScheme="green"
                      onClick={handleStartA}
                      isDisabled={runningA || bootingA}
                      isLoading={loadingStartA || bootingA}
                    >
                      Iniciar
                    </Button>
                    <Button
                      size="sm"
                      colorScheme="red"
                      variant="outline"
                      onClick={handleStopA}
                      isDisabled={!runningA || bootingA}
                      isLoading={loadingStopA}
                    >
                      Parar
                    </Button>
                    <Button size="sm" colorScheme="blue" isDisabled>
                      Aplicar
                    </Button>
                  </HStack>
                </Box>
              </Flex>

              {/* Stream */}
              <Box
                borderWidth="1px"
                borderRadius="md"
                bg="bg.subtle"
                h="260px"
                mb={4}
                overflow="hidden"
                position="relative"
              >
                {/* Overlay de boot */}
                {bootingA && (
                  <Center position="absolute" inset={0} bg="blackAlpha.400" zIndex={1}>
                    <Spinner color="#800020" thickness="3px" />
                  </Center>
                )}
                <CameraStream
                  cameraId={CAMERA_ID_A}
                  online={runningA}
                  ratio={16/9}
                  showSpinner={false}
                  spinnerColor="#800020"
                />
              </Box>

              {/* Footer (placeholder) */}
              <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" h="52px" />
            </Box>
          </GridItem>

          {/* Linha B (ainda estática) */}
          <GridItem>
            <Box borderWidth="1px" borderRadius="md" bg="bg.surface" p={4}>
              <Heading size="md" mb={4}>Linha B</Heading>

              <Flex direction={{ base: 'column', md: 'row' }} gap={6} mb={4}>
                {/* DataList */}
                <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" p={3} flex="1">
                  <DataList.Root orientation="horizontal" divideY="1px">
                    <DataList.Item>
                      <DataList.ItemLabel>Status</DataList.ItemLabel>
                      <DataList.ItemValue>
                        <Badge colorScheme="gray">Offline</Badge>
                      </DataList.ItemValue>
                    </DataList.Item>
                    <DataList.Item>
                      <DataList.ItemLabel>Item</DataList.ItemLabel>
                      <DataList.ItemValue>item_detector</DataList.ItemValue>
                    </DataList.Item>
                    <DataList.Item>
                      <DataList.ItemLabel>Perfil</DataList.ItemLabel>
                      <DataList.ItemValue>— × —</DataList.ItemValue>
                    </DataList.Item>
                  </DataList.Root>
                </Box>

                {/* Select v3 + botões (placeholders) */}
                <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" p={3} flex="1">
                  <Select.Root collection={produtosCollection} size="sm" width="100%">
                    <Select.HiddenSelect />
                    <Select.Label>Trocar produto</Select.Label>
                    <Select.Control>
                      <Select.Trigger>
                        <Select.ValueText placeholder="Selecione um produto" />
                      </Select.Trigger>
                      <Select.IndicatorGroup>
                        <Select.Indicator />
                      </Select.IndicatorGroup>
                    </Select.Control>
                    <Portal>
                      <Select.Positioner>
                        <Select.Content>
                          {categorias.map(([categoria, items]) => (
                            <Select.ItemGroup key={categoria}>
                              <Select.ItemGroupLabel>{categoria}</Select.ItemGroupLabel>
                              {items.map((item) => (
                                <Select.Item item={item} key={item.value}>
                                  {item.label}
                                  <Select.ItemIndicator />
                                </Select.Item>
                              ))}
                            </Select.ItemGroup>
                          ))}
                        </Select.Content>
                      </Select.Positioner>
                    </Portal>
                  </Select.Root>

                  <HStack spacing={2} mt={3}>
                    <Button size="sm" colorScheme="green">Iniciar</Button>
                    <Button size="sm" colorScheme="red" variant="outline">Parar</Button>
                    <Button size="sm" colorScheme="blue">Aplicar</Button>
                  </HStack>
                </Box>
              </Flex>

              <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" h="260px" mb={4} />
              <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" h="52px" />
            </Box>
          </GridItem>
        </Grid>

        {/* Logs globais (placeholder) */}
        <Box borderWidth="1px" borderRadius="md" bg="bg.surface" p={4} mt={6}>
          <Heading size="sm" mb={2}>Logs</Heading>
          <Box borderWidth="1px" borderRadius="md" bg="bg.subtle" h="140px" />
        </Box>
      </Container>
    </Box>
  )
}