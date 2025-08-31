import { useEffect, useState } from 'react'
import {
  Box,
  Container,
  Flex,
  Heading,
  Text,
  Button,
  IconButton,
  HStack,
  Spinner,
  Circle,
  Card,
  Stat,
  Badge,
  VStack,
  SimpleGrid,
} from '@chakra-ui/react'
import MenuIcon from '@mui/icons-material/Menu'
import CloseIcon from '@mui/icons-material/Close'

// Removed Vite template CSS; Chakra handles styles

function StatusDot({ status }) {
  const color = status === 'ok' ? 'green.400' : 'red.400'
  return <Circle size="10px" bg={color} />
}

function setorStatus(active, total) {
  if (!total) return { color: 'gray', label: 'Sem câmeras' }
  if (active === 0) return { color: 'red', label: 'Parado' }
  if (active === total) return { color: 'green', label: 'Ativo' }
  return { color: 'yellow', label: 'Parcial' }
}

const API_URL = 'http://localhost:8000/api'

function useFetch(url, setter) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await fetch(url)
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
        const data = await response.json()
        setter(data)
      } catch (err) {
        setError(err.message)
        console.error('Fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [url, setter])

  return { loading, error }
}

function App() {
  const [status, setStatus] = useState(null)
  const [overview, setOverview] = useState(null)
  const [setores, setSetores] = useState([])
  const [time, setTime] = useState(new Date())
  const [isSidebarOpen, setSidebarOpen] = useState(true)
  const [isSetoresOpen, setIsSetoresOpen] = useState(false)

  const { loading: statusLoading, error: statusError } = useFetch(API_URL, setStatus)
  const { loading: overviewLoading, error: overviewError } = useFetch(`${API_URL}/overview`, setOverview)
  const { loading: setoresLoading, error: setoresError } = useFetch(`${API_URL}/setores`, setSetores)

  const reloadAll = () => {
    // Trigger re-fetch by updating the URLs or calling fetch functions directly
    window.location.reload()
  }

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const globalLoading = statusLoading || overviewLoading || setoresLoading

  return (
    <Flex h="100vh" bg="bg.canvas">
      {/* Sidebar (agora com animação) */}
      <Box
        as="aside"
        w={isSidebarOpen ? { base: '100vw', sm: '85vw', md: '70vw', lg: '20vw', xl: '20vw' } : 0}
        flexShrink={0}
        bg="bg.subtle"
        borderRight={isSidebarOpen ? '1px' : '0px'}
        borderColor="border.default"
        transition="width 0.3s ease"
        overflow="hidden"
        whiteSpace="nowrap"
      >
        <Box minW={{ base: '100vw', sm: '85vw', md: '70vw', lg: '20vw', xl: '20vw' }}>
          <Flex align="center" justify="space-between" px="3" py="2" borderBottom="1px" borderColor="border.default">
            <Heading size="sm">Menu</Heading>
            <IconButton
              aria-label="Fechar menu"
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(false)}
            >
              <CloseIcon />
            </IconButton>
          </Flex>
          <Box p="3">
            <VStack align="stretch" spacing={2}>
              <Button
                variant="ghost"
                justifyContent="flex-start"
                leftIcon={<Box as="span" className="material-symbols-outlined">home</Box>}
              >
                Página Inicial
              </Button>
              <Button
                variant="ghost"
                justifyContent="space-between"
                w="100%"
                onClick={() => setIsSetoresOpen(!isSetoresOpen)}
                leftIcon={<Box as="span" className="material-symbols-outlined">grid_view</Box>}
                rightIcon={<Box as="span" className="material-symbols-outlined">{isSetoresOpen ? 'expand_less' : 'expand_more'}</Box>}
              >
                Setores
              </Button>
              <Box
                overflow="hidden"
                maxHeight={isSetoresOpen ? "120px" : "0"}
                transition="max-height 0.3s ease"
              >
                <VStack align="stretch" spacing={1} pl={6} mt={1}>
                  <Button variant="ghost" justifyContent="flex-start" size="sm">Líquidos</Button>
                  <Button variant="ghost" justifyContent="flex-start" size="sm">Sólidos</Button>
                  <Button variant="ghost" justifyContent="flex-start" size="sm">Semi-sólidos</Button>
                </VStack>
              </Box>
              <Button
                variant="ghost"
                justifyContent="flex-start"
                leftIcon={<Box as="span" className="material-symbols-outlined">info</Box>}
              >
                Sobre
              </Button>
            </VStack>
          </Box>
        </Box>
      </Box>

      {/* Main Content Area */}
      <Flex flex="1" direction="column">
        {/* Header (movido para cá) */}
        <Flex as="header" bg="bg.surface" borderBottom="1px" borderColor="border.default" px={{ base: 3, md: 6 }} py={{ base: 2, md: 3 }} align="center" wrap="wrap" gap={2} position="relative">
          <HStack spacing={3}>
            {!isSidebarOpen && (
              <IconButton
                aria-label={'Abrir menu'}
                variant="ghost"
                size="sm"
                onClick={() => setSidebarOpen(true)}
                color="fg.muted"
              >
                <MenuIcon />
              </IconButton>
            )}
          </HStack>

          {/* Título centralizado */}
          <Box position="absolute" left="50%" transform="translateX(-50%)" pointerEvents="none">
            <Heading size="md" textAlign="center">SIAC Industrial</Heading>
          </Box>

          <HStack spacing={4} ml={{ base: 0, md: 'auto' }} align="center" w={{ base: '100%', md: 'auto' }} justify={{ base: 'space-between', md: 'flex-end' }}>
            {statusLoading ? (
              <Spinner size="sm" />
            ) : (
              <HStack>
                <StatusDot status={status?.status === 'ok' ? 'ok' : 'error'} />
                <Text fontSize="sm" color="fg.default">
                  {status?.status === 'ok' ? 'Online' : 'Offline'}
                </Text>
              </HStack>
            )}
            <Text fontSize="sm" color="fg.muted" minW="120px" textAlign="right" display={{ base: 'none', sm: 'block' }}>
              {time.toLocaleTimeString()}
            </Text>
            <Button size="sm" onClick={reloadAll} colorScheme="blue">
              Atualizar
            </Button>
          </HStack>
        </Flex>

        {/* Content */}
        <Box flex="1" overflowY="auto">
          {/* Loading overlay */}
          {globalLoading && (
            <Flex position="fixed" inset={0} bg="blackAlpha.400" align="center" justify="center" zIndex={10}>
              <Spinner size="xl" color="blue.500" />
            </Flex>
          )}

          <Container maxW="container.xl" py={6}>
            {/* Overview Cards */}
            {overview && (
              <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
                <Card>
                  <Box p={6}>
                    <Stat>
                      <Text fontSize="sm" color="fg.muted">Total de Setores</Text>
                      <Text fontSize="2xl" fontWeight="bold">{overview.total_setores}</Text>
                    </Stat>
                  </Box>
                </Card>
                <Card>
                  <Box p={6}>
                    <Stat>
                      <Text fontSize="sm" color="fg.muted">Setores Ativos</Text>
                      <Text fontSize="2xl" fontWeight="bold" color="green.500">{overview.setores_ativos}</Text>
                    </Stat>
                  </Box>
                </Card>
                <Card>
                  <Box p={6}>
                    <Stat>
                      <Text fontSize="sm" color="fg.muted">Total de Câmeras</Text>
                      <Text fontSize="2xl" fontWeight="bold">{overview.total_cameras}</Text>
                    </Stat>
                  </Box>
                </Card>
                <Card>
                  <Box p={6}>
                    <Stat>
                      <Text fontSize="sm" color="fg.muted">Câmeras Ativas</Text>
                      <Text fontSize="2xl" fontWeight="bold" color="green.500">{overview.cameras_ativas}</Text>
                    </Stat>
                  </Box>
                </Card>
              </SimpleGrid>
            )}

            {/* Setores Grid */}
            <Heading size="lg" mb={4}>Setores</Heading>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
              {setores.map((setor) => (
                <Card key={setor.id}>
                  <Box p={6}>
                    <Flex justify="space-between" align="center" mb={4}>
                      <Heading size="md">{setor.name}</Heading>
                      <Badge colorScheme={setorStatus(setor.active_cameras, setor.total_cameras).color}>
                        {setorStatus(setor.active_cameras, setor.total_cameras).label}
                      </Badge>
                    </Flex>
                    <Text fontSize="sm" color="fg.muted">
                      {setor.active_cameras} de {setor.total_cameras} câmeras ativas
                    </Text>
                  </Box>
                </Card>
              ))}
            </SimpleGrid>
          </Container>
        </Box>
      </Flex>
    </Flex>
  )
}

export default App
