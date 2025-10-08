import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ChakraProvider, createSystem, defaultConfig } from '@chakra-ui/react'
import { BrowserRouter } from 'react-router-dom'
// Removed Vite template CSS; Chakra handles global styles
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter basename="/app">
      <ChakraProvider value={createSystem(defaultConfig)}>
        <App />
      </ChakraProvider>
    </BrowserRouter>
  </StrictMode>,
)
