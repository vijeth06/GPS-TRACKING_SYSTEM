/**
 * GPS Tracking System - Main Application
 * 
 * Real-Time GPS Tracking and Movement Intelligence System
 * 
 * Architecture:
 *   React Dashboard
 *        ↑
 *   WebSocket (Socket.IO)
 *        ↑
 *   FastAPI Backend
 */

import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
