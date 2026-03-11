/**
 * Socket.IO Service
 * 
 * Handles real-time WebSocket communication with the backend.
 * 
 * Events:
 *   - device_location_update: New GPS location received
 *   - alert_update: New alert generated
 *   - device_status_change: Device online/offline
 */

import { io } from 'socket.io-client'

class SocketService {
  constructor() {
    this.socket = null
    this.listeners = new Map()
    this.isConnected = false
  }

  /**
   * Connect to the WebSocket server
   */
  connect() {
    if (this.socket && this.isConnected) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      // Connect to the backend Socket.IO server
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

      // Set up event forwarding
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

  /**
   * Disconnect from the server
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.isConnected = false
    }
  }

  /**
   * Subscribe to location updates
   * @param {Function} callback - Called with location data
   * @returns {Function} Unsubscribe function
   */
  onLocationUpdate(callback) {
    return this._addListener('locationUpdate', callback)
  }

  /**
   * Subscribe to alert updates
   * @param {Function} callback - Called with alert data
   * @returns {Function} Unsubscribe function
   */
  onAlertUpdate(callback) {
    return this._addListener('alertUpdate', callback)
  }

  /**
   * Subscribe to device status changes
   * @param {Function} callback - Called with status data
   * @returns {Function} Unsubscribe function
   */
  onStatusChange(callback) {
    return this._addListener('statusChange', callback)
  }

  /**
   * Subscribe to updates for a specific device
   * @param {string} deviceId - Device to subscribe to
   */
  subscribeToDevice(deviceId) {
    if (this.socket && this.isConnected) {
      this.socket.emit('subscribe_device', { device_id: deviceId })
    }
  }

  /**
   * Unsubscribe from a specific device
   * @param {string} deviceId - Device to unsubscribe from
   */
  unsubscribeFromDevice(deviceId) {
    if (this.socket && this.isConnected) {
      this.socket.emit('unsubscribe_device', { device_id: deviceId })
    }
  }

  /**
   * Add a listener for an event type
   * @private
   */
  _addListener(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType).add(callback)

    // Return unsubscribe function
    return () => {
      const listeners = this.listeners.get(eventType)
      if (listeners) {
        listeners.delete(callback)
      }
    }
  }

  /**
   * Notify all listeners of an event
   * @private
   */
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

// Export singleton instance
const socketService = new SocketService()
export default socketService
