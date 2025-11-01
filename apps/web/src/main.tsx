import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { StrictMode } from 'react'
import App from './App'

createRoot(document.getElementById('root')!).render(
     <StrictMode>
        <App />
    </StrictMode>,
)
