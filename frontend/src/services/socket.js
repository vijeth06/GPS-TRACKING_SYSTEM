
import { io } from 'socket.io-client'

class SocketService {
  constructor() {
    this.socket = null
    this.listeners = new Map()
    this.isConnected = false
  }

  connect() {
    if (this.socket && this.isConnected) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      this.socket = io('http://localhost:8000', {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      })

      this.socket.on('connect', () => {
        console.log('Socket.IO connected:', this.socket.id)
        this.isConnected = true
        resolve()
      })

      this.socket.on('disconnect', (reason) => {
        console.log('Socket.IO disconnected:', reason)
        this.isConnected = false
      })

      this.socket.on('connect_error', (error) => {
        console.error('Socket.IO connection error:', error)
        reject(error)
      })

      this.socket.on('device_location_update', (data) => {
        this._notifyListeners('locationUpdate', data)
      })

      this.socket.on('alert_update', (data) => {
        this._notifyListeners('alertUpdate', data)
      })

      this.socket.on('device_status_change', (data) => {
        this._notifyListeners('statusChange', data)
      })
    })
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.isConnected = false
    }
  }

  onLocationUpdate(callback) {
    return this._addListener('locationUpdate', callback)
  }

  onAlertUpdate(callback) {
    return this._addListener('alertUpdate', callback)
  }

  onStatusChange(callback) {
    return this._addListener('statusChange', callback)
  }

  subscribeToDevice(deviceId) {
    if (this.socket && this.isConnected) {
      this.socket.emit('subscribe_device', { device_id: deviceId })
    }
  }

  unsubscribeFromDevice(deviceId) {
    if (this.socket && this.isConnected) {
      this.socket.emit('unsubscribe_device', { device_id: deviceId })
    }
  }

  _addListener(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType).add(callback)

    return () => {
      const listeners = this.listeners.get(eventType)
      if (listeners) {
        listeners.delete(callback)
      }
    }
  }

  _notifyListeners(eventType, data) {
    const listeners = this.listeners.get(eventType)
    if (listeners) {
      listeners.forEach((callback) => {
        try {
          callback(data)
        } catch (error) {
          console.error('Socket listener error:', error)
        }
      })
    }
  }
}

const socketService = new SocketService()
export default socketService