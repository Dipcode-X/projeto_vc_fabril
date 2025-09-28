// frontend/src/pages/LiquidosPage.jsx
import {
    Box,
    Flex,
    Grid,
    GridItem,
    Stack,
    HStack,
    VStack,
    SimpleGrid,
    Heading,
    Text,
    Badge,
    Tag,
    Divider,
    Spacer,
    Button,
    IconButton,
    Select,
    NumberInput,
    NumberInputField,
    Switch,
    Input,
    Tabs,
    TabList,
    TabPanels,
    Tab,
    TabPanel,
    Tooltip,
    Progress,
    CircularProgress,
    AspectRatio,
    Image,
    Skeleton,
  } from '@chakra-ui/react'
  import { InfoOutlineIcon, RepeatIcon } from '@chakra-ui/icons'
  import { useMemo } from 'react'
  
  export default function LiquidosPage() {
    // Mock de dados para layout estático
    const kpis = useMemo(
      () => ([
        { label: 'Câmeras ativas', value: 1, color: (v) => (v > 0 ? 'green.500' : 'green.700') },
        { label: 'Total de câmeras', value: 2 },
        { label: 'Itens por camada', value: '6 × 1' },
        { label: 'Contagem atual', value: '1 / 6' },
      ]),
      []
    )
  
    const linhaA = {
      nome: 'Linha A',
      online: true,
      item: 'ac_madepil',
      caixa: 'roi: 19×28',
      perfil: '6 × 1',
      divisor: 'Não',
      cameras: '1/1',
      contagem: '1/6',
    }
  
    const linhaB = {
      nome: 'Linha B',
      online: false,
      item: 'item_detector',
      caixa: 'roi: —',
      perfil: '— × —',
      divisor: 'Sim',
      cameras: '—/—',
      contagem: '—/—',
    }
  
    const subtle = 'fg.muted'
    const cardProps = {
      borderWidth: '1px',
      borderRadius: 'md',
      bg: 'bg.surface',
      boxShadow: 'sm',
    }
  
    return (
      <Box bg="bg.canvas" minH="100vh" p={{ base: 4, md: 6 }}>
        {/* Topbar */}
        <Flex align="center" gap={4} mb={6}>
          <Heading size="lg">SIAC Industrial • Líquidos</Heading>
          <Tag colorScheme="green">Online</Tag>
          <Spacer />
          <Tooltip label="Atualizar">
            <IconButton aria-label="Atualizar" icon={<RepeatIcon />} variant="ghost" />
          </Tooltip>
        </Flex>
  
        {/* KPIs */}
        <SimpleGrid columns={{ base: 1, md: 4 }} gap={4} mb={6}>
          {kpis.map((kpi, i) => (
            <Box key={i} {...cardProps}>
              <Box p={5}>
                <VStack align="flex-start" spacing={1}>
                  <Text fontSize="sm" color={subtle}>{kpi.label}</Text>
                  <Text
                    fontSize="2xl"
                    fontWeight="bold"
                    color={typeof kpi.value === 'number' && kpi.color ? kpi.color(kpi.value) : undefined}
                  >
                    {kpi.value}
                  </Text>
                  <Text fontSize="xs" color={subtle}>atualizado agora</Text>
                </VStack>
              </Box>
            </Box>
          ))}
        </SimpleGrid>
  
        {/* 2 colunas principais */}
        <Grid templateColumns={{ base: '1fr', xl: '1fr 1fr' }} gap={6}>
          {/* Linha A */}
          <GridItem>
            <Box {...cardProps}>
              <Box p={5} borderBottom="1px" borderColor="border.default">
                <HStack align="start" w="full">
                  <Box>
                    <Heading size="md">{linhaA.nome}</Heading>
                    <HStack mt={2} gap={2} wrap="wrap">
                      <Badge colorScheme={linhaA.online ? 'green' : 'gray'}>
                        {linhaA.online ? 'Online' : 'Offline'}
                      </Badge>
                      <Tag size="sm">item: {linhaA.item}</Tag>
                      <Tag size="sm">caixa: {linhaA.caixa}</Tag>
                      <Tag size="sm" variant="subtle">perfil: {linhaA.perfil}</Tag>
                      <Tag size="sm">divisor: {linhaA.divisor}</Tag>
                      <Tag size="sm">câmeras: {linhaA.cameras}</Tag>
                      <Tag size="sm">contagem: {linhaA.contagem}</Tag>
                    </HStack>
                  </Box>
                  <Spacer />
                  <Tooltip label="Informações da linha">
                    <Box as={InfoOutlineIcon} color={subtle} />
                  </Tooltip>
                </HStack>
              </Box>
  
              <Box p={5}>
                {/* Controles */}
                <Stack
                  direction={{ base: 'column', md: 'row' }}
                  gap={4}
                  align="start"
                  mb={4}
                  flexWrap="wrap"
                >
                  <Box minW="230px">
                    <Text fontSize="sm" mb={1}>Trocar produto</Text>
                    <HStack gap={2}>
                      <Select placeholder="selecione…">
                        <option>ac_madepil</option>
                        <option>glifosato_dipil_480</option>
                      </Select>
                      <Button>Aplicar</Button>
                    </HStack>
                  </Box>
  
                  <Box>
                    <Text fontSize="sm" mb={1}>Camada</Text>
                    <NumberInput w="120px" min={1} defaultValue={1}>
                      <NumberInputField />
                    </NumberInput>
                  </Box>
  
                  <Box>
                    <Text fontSize="sm" mb={1}>Contagem</Text>
                    <NumberInput w="140px" min={0} defaultValue={6}>
                      <NumberInputField />
                    </NumberInput>
                  </Box>
  
                  <Box>
                    <Text fontSize="sm" mb={1}>Divisor</Text>
                    <HStack gap={2}>
                      <Switch />
                      <Text fontSize="sm" color={subtle}>desligado</Text>
                    </HStack>
                  </Box>
  
                  <Spacer />
                  <HStack gap={2}>
                    <Button colorScheme="green">Iniciar</Button>
                    <Button colorScheme="red" variant="outline">Parar</Button>
                  </HStack>
                </Stack>
  
                <Divider my={4} />
  
                {/* Stream */}
                <Heading size="sm" mb={2}>Stream</Heading>
                <AspectRatio ratio={16 / 9} rounded="lg" overflow="hidden" bg="black">
                  <Skeleton isLoaded={false}>
                    <Image alt="stream" src="" objectFit="cover" />
                  </Skeleton>
                </AspectRatio>
              </Box>
  
              <Box p={5} borderTop="1px" borderColor="border.default">
                <HStack w="full" gap={3}>
                  <Text fontSize="sm" color={subtle}>Processamento</Text>
                  <Progress flex="1" value={30} rounded="full" />
                  <CircularProgress value={30} />
                </HStack>
              </Box>
            </Box>
          </GridItem>
  
          {/* Linha B */}
          <GridItem>
            <Box {...cardProps}>
              <Box p={5} borderBottom="1px" borderColor="border.default">
                <HStack w="full" gap={3}>
                  <Heading size="md">{linhaB.nome}</Heading>
                  <Badge colorScheme={linhaB.online ? 'green' : 'gray'}>
                    {linhaB.online ? 'Online' : 'Offline'}
                  </Badge>
                  <Tag size="sm">item: {linhaB.item}</Tag>
                  <Tag size="sm">caixa: {linhaB.caixa}</Tag>
                  <Tag size="sm" variant="subtle">perfil: {linhaB.perfil}</Tag>
                  <Spacer />
                  <Tooltip label="Recarregar stream">
                    <IconButton aria-label="reload" icon={<RepeatIcon />} variant="ghost" />
                  </Tooltip>
                </HStack>
              </Box>
  
              <Box p={5}>
                <Stack direction={{ base: 'column', md: 'row' }} gap={4} mb={4} flexWrap="wrap">
                  <Box minW="230px">
                    <Text fontSize="sm" mb={1}>Trocar produto</Text>
                    <HStack gap={2}>
                      <Select placeholder="selecione…">
                        <option>glifosato_dipil_480</option>
                      </Select>
                      <Button>Aplicar</Button>
                    </HStack>
                  </Box>
  
                  <Box>
                    <Text fontSize="sm" mb={1}>Camada</Text>
                    <Input w="120px" placeholder="—" isDisabled />
                  </Box>
  
                  <Box>
                    <Text fontSize="sm" mb={1}>Contagem</Text>
                    <Input w="140px" placeholder="—" isDisabled />
                  </Box>
  
                  <Spacer />
                  <HStack gap={2}>
                    <Button colorScheme="green" isDisabled>Iniciar</Button>
                    <Button colorScheme="red" variant="outline" isDisabled>Parar</Button>
                  </HStack>
                </Stack>
  
                <Divider my={4} />
  
                <Heading size="sm" mb={2}>Stream</Heading>
                <AspectRatio ratio={16 / 9} rounded="lg" bg="gray.900" color="gray.400">
                  <Flex align="center" justify="center">
                    <Text>Sem stream disponível</Text>
                  </Flex>
                </AspectRatio>
  
                <Tabs mt={6} variant="enclosed">
                  <TabList>
                    <Tab>Logs</Tab>
                    <Tab>Diagnóstico</Tab>
                  </TabList>
                  <TabPanels>
                    <TabPanel>
                      <VStack align="stretch" spacing={2} fontSize="sm">
                        <Text>[15:20:47] aguardando sinal…</Text>
                        <Text>[15:21:02] câmera offline</Text>
                      </VStack>
                    </TabPanel>
                    <TabPanel>
                      <Text fontSize="sm" color={subtle}>Nenhum erro crítico.</Text>
                    </TabPanel>
                  </TabPanels>
                </Tabs>
              </Box>
            </Box>
          </GridItem>
        </Grid>
  
        {/* Logs globais */}
        <Box mt={6} {...cardProps}>
          <Box p={5} borderBottom="1px" borderColor="border.default">
            <Heading size="sm">Logs</Heading>
          </Box>
          <Box p={5}>
            <VStack align="stretch" spacing={1} fontSize="sm" color={subtle} maxH="220px" overflow="auto">
              <Text>[15:20:45] sistema iniciado</Text>
              <Text>[15:20:47] conexão estabelecida</Text>
            </VStack>
          </Box>
        </Box>
      </Box>
    )
  }