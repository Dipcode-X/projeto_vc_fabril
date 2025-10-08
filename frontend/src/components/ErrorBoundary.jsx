import React from 'react'
import { Box, Heading, Text, Button } from '@chakra-ui/react'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, errorInfo) {
    // Log for diagnostics
    console.error('ErrorBoundary caught:', error, errorInfo)
    this.setState({ errorInfo })
  }

  handleReload = () => {
    if (typeof window !== 'undefined') window.location.reload()
  }

  render() {
    if (this.state.error) {
      return (
        <Box p={6}>
          <Heading size="md" mb={3}>Ocorreu um erro na interface{this.props.section ? ` — seção: ${this.props.section}` : ''}</Heading>
          <Text fontSize="sm" color="fg.muted" mb={2}>
            {String(this.state.error?.message || this.state.error)}
          </Text>
          {this.state.errorInfo?.componentStack && (
            <Box as="pre" bg="bg.subtle" p={3} borderRadius="md" overflow="auto" fontSize="xs" maxH="40vh">
              {this.state.errorInfo.componentStack}
            </Box>
          )}
          <Button mt={4} onClick={this.handleReload} colorScheme="blue">Recarregar</Button>
        </Box>
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
