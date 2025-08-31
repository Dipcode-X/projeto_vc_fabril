import { Box, Heading } from '@chakra-ui/react'
import { useParams } from 'react-router-dom'

function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1)
}

function SetorPage() {
  const { setorNome } = useParams()

  return (
    <Box p={8}>
      <Heading color="fg.muted">{capitalizeFirstLetter(setorNome)}</Heading>
    </Box>
  )
}

export default SetorPage
