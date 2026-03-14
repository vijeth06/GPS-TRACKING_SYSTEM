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
import Login from './pages/Login'
import { AuthProvider, useAuth } from './context/AuthContext'

function AppRoutes() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading session...</div>
  }

  return (
    <Routes>
      {isAuthenticated ? <Route path="/" element={<Dashboard />} /> : <Route path="/" element={<Login />} />}
      <Route path="*" element={isAuthenticated ? <Dashboard /> : <Login />} />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-gray-100">
          <AppRoutes />
        </div>
      </Router>
    </AuthProvider>
  )
}

export default App
