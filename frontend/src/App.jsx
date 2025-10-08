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
  CloseButton,
  Spinner,
  Circle,
  VStack,
  SimpleGrid,
  Toaster,
  ToastRoot,
  ToastTitle,
  ToastDescription,
  ToastIndicator,
  ToastCloseTrigger,
} from '@chakra-ui/react'
import { Routes, Route, Link } from 'react-router-dom'
import SetorPage from './pages/SetorPage.jsx'
import CamerasPage from './pages/CamerasPage.jsx'
import LiquidosPage from './pages/LiquidosPage.jsx'
import { toaster } from './toaster.js'
import ErrorBoundary from './components/ErrorBoundary.jsx'

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

const API_URL = '/api/v1'

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
  const [isSidebarOpen, setSidebarOpen] = useState(false)
  const [isSetoresOpen, setIsSetoresOpen] = useState(false)

  const { loading: statusLoading } = useFetch(`${API_URL}/status`, setStatus)
  const { loading: overviewLoading } = useFetch(`${API_URL}/dashboard`, setOverview)
  const { loading: setoresLoading } = useFetch(`${API_URL}/setores`, setSetores)

  const reloadAll = () => window.location.reload()

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const globalLoading = statusLoading || overviewLoading || setoresLoading

  // Limita a 3 setores visíveis (usado somente para os contadores)
  const setoresVisiveis = Array.isArray(setores) ? setores.slice(0, 3) : []

  // Contadores (com base apenas nos 3 setores visíveis)
  const totalSetores = setoresVisiveis.length
  const setoresAtivos = setoresVisiveis.filter((s) => Number(s?.cameras_ativas ?? 0) > 0).length

  const camerasTotal = overview?.cameras_total ?? 0
  const camerasAtivas = overview?.cameras_active ?? 0

  function DashboardHome() {
    return (
      <Container maxW="container.xl" py={6}>
        {/* Overview Cards */}
        {overview && (
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
            <Box borderWidth="1px" borderRadius="md" bg="bg.surface">
              <Box p={6}>
                <Text fontSize="sm" color="fg.muted">Total de Setores</Text>
                <Text fontSize="2xl" fontWeight="bold">{String(totalSetores)}</Text>
              </Box>
            </Box>
            <Box borderWidth="1px" borderRadius="md" bg="bg.surface">
              <Box p={6}>
                <Text fontSize="sm" color="fg.muted">Setores Ativos</Text>
                <Text fontSize="2xl" fontWeight="bold" color="green.500">{String(setoresAtivos)}</Text>
              </Box>
            </Box>
            <Box borderWidth="1px" borderRadius="md" bg="bg.surface">
              <Box p={6}>
                <Text fontSize="sm" color="fg.muted">Total de Câmeras</Text>
                <Text fontSize="2xl" fontWeight="bold">{String(camerasTotal)}</Text>
              </Box>
            </Box>
            <Box borderWidth="1px" borderRadius="md" bg="bg.surface">
              <Box p={6}>
                <Text fontSize="sm" color="fg.muted">Câmeras Ativas</Text>
                <Text fontSize="2xl" fontWeight="bold" color="green.500">{String(camerasAtivas)}</Text>
              </Box>
            </Box>
          </SimpleGrid>
        )}

        {/* Listagem de setores removida nesta etapa */}
      </Container>
    )
  }

  return (
    <Flex h="100vh" bg="bg.canvas">
      {/* Sidebar */}
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
            <CloseButton aria-label="Fechar menu" size="sm" onClick={() => setSidebarOpen(false)} />
          </Flex>
          <Box p="3">
            <VStack align="stretch" spacing={2}>
              <Button
                as={Link}
                to="/"
                variant="ghost"
                justifyContent="flex-start"
                leftIcon={<span style={{ fontSize: '16px' }}>🏠</span>}
              >
                Página Inicial
              </Button>
              <Button
                variant="ghost"
                justifyContent="space-between"
                w="100%"
                onClick={() => setIsSetoresOpen(!isSetoresOpen)}
                leftIcon={<span style={{ fontSize: '16px' }}>📋</span>}
                rightIcon={<span style={{ fontSize: '14px' }}>{isSetoresOpen ? '▴' : '▾'}</span>}
              >
                Setores
              </Button>
              <Box
                overflow="hidden"
                maxHeight={isSetoresOpen ? '120px' : '0'}
                transition="max-height 0.3s ease"
              >
                <VStack align="stretch" spacing={1} pl={6} mt={1}>
                  <Button as={Link} to="/setores/liquidos" variant="ghost" justifyContent="flex-start" size="sm">Líquidos</Button>
                  <Button variant="ghost" justifyContent="flex-start" size="sm">Sólidos</Button>
                  <Button variant="ghost" justifyContent="flex-start" size="sm">Semi-sólidos</Button>
                </VStack>
              </Box>
              <Button
                as={Link}
                to="/cameras"
                variant="ghost"
                justifyContent="flex-start"
                leftIcon={<span style={{ fontSize: '16px' }}>🎥</span>}
              >
                Câmeras
              </Button>
              <Button
                variant="ghost"
                justifyContent="flex-start"
                leftIcon={<span style={{ fontSize: '16px' }}>ℹ️</span>}
              >
                Sobre
              </Button>
            </VStack>
          </Box>
        </Box>
      </Box>

      {/* Main Content Area */}
      <Flex flex="1" direction="column">
        {/* Header */}
        <Flex
          as="header"
          bg="bg.surface"
          borderBottom="1px"
          borderColor="border.default"
          px={{ base: 3, md: 6 }}
          py={{ base: 2, md: 3 }}
          align="center"
          wrap="wrap"
          gap={2}
          position="relative"
        >
          {/* Hamburger: aparece somente quando o menu está FECHADO */}
          <HStack spacing={3} position="relative" zIndex={2}>
            {!isSidebarOpen && (
              <IconButton
                aria-label="Abrir menu"
                variant="ghost"
                size="sm"
                onClick={() => setSidebarOpen(true)}
                color="whiteAlpha.900"
                _hover={{ bg: 'whiteAlpha.200' }}
              >
                <Box as="span" fontSize="24px" lineHeight="1" color="whiteAlpha.900">☰</Box>
              </IconButton>
            )}
          </HStack>

          {/* Título centralizado */}
          <Box position="absolute" left="50%" transform="translateX(-50%)" pointerEvents="none">
            <Heading size="md" textAlign="center">SIAC Industrial</Heading>
          </Box>

          {/* À direita do header */}
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

          {/* Rotas da aplicação */}
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<DashboardHome />} />
              <Route path="/setores/liquidos" element={<LiquidosPage />} />
              <Route path="/setores/:setorNome" element={<SetorPage />} />
              <Route path="/cameras" element={<CamerasPage />} />
            </Routes>
          </ErrorBoundary>
        </Box>
      </Flex>

      {/* Toaster */}
      <Toaster toaster={toaster} placement="bottom-end">
        {(t) => (
          <ToastRoot>
            <ToastIndicator />
            <Box>
              <ToastTitle>{t.title}</ToastTitle>
              <ToastDescription>{t.description}</ToastDescription>
            </Box>
            <ToastCloseTrigger />
          </ToastRoot>
        )}
      </Toaster>
    </Flex>
  )
}

export default App