// Loads React, global styles, and the dashboard component.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Finds the root HTML element and renders the dashboard.
createRoot(document.getElementById('root')).render(
  // Enables React’s extra development lifecycle checks; polling cleanup prevents duplicate
  // lingering checks.
  <StrictMode>
    <App />
  </StrictMode>,
)
