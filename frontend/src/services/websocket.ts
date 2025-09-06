export interface OrderBookLevel {
  price: number
  size: number
  level: number
}

export interface OrderBookData {
  symbol: string
  timestamp: string
  tick_id: string
  is_indicative: boolean
  best_bid: number
  best_ask: number
  mid_price: number
  spread: number
  spread_bps: number
  bids: OrderBookLevel[]
  asks: OrderBookLevel[]
  latest_price: {
    price: number
    source: string
  }
  levels: {
    bid_levels: number
    ask_levels: number
    trade_count: number
  }
  metadata: {
    total_entries: number
    has_trades: boolean
    book_depth: number
  }
}

export interface OrderBookMessage {
  type: 'orderbook'
  symbol: string
  request_id: string
  data: OrderBookData
  timestamp: string
}

export interface WebSocketMessage {
  type: string
  symbol?: string
  levels?: number
  error?: string
  data?: any
  timestamp?: string
}

export interface SubscribeMessage {
  type: 'subscribe'
  symbol: string
  levels: number
}

export interface UnsubscribeMessage {
  type: 'unsubscribe'
  symbol: string
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectInterval = 1000
  private isConnecting = false
  private messageQueue: any[] = []
  private eventListeners: Map<string, ((data: any) => void)[]> = new Map()

  constructor(private wsUrl: string) {}

  connect(token: string): Promise<boolean> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve(true)
        return
      }

      if (this.isConnecting) {
        reject(new Error('Connection already in progress'))
        return
      }

      this.isConnecting = true
      const url = `${this.wsUrl}/orderbook?token=${encodeURIComponent(token)}`

      try {
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
          console.log('WebSocket connected to orderbook')
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.processMessageQueue()
          this.emit('connected', null)
          resolve(true)
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason)
          this.isConnecting = false
          this.ws = null
          this.emit('disconnected', { code: event.code, reason: event.reason })
          
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect(token)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.isConnecting = false
          this.emit('error', error)
          reject(error)
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error, event.data)
          }
        }

      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    this.reconnectAttempts = this.maxReconnectAttempts // Prevent reconnection
  }

  subscribe(symbol: string, levels: number = 5) {
    const message: SubscribeMessage = {
      type: 'subscribe',
      symbol,
      levels
    }
    console.log('Sending subscribe message (preserving exact case):', message)
    this.sendMessage(message)
  }

  unsubscribe(symbol: string) {
    const message: UnsubscribeMessage = {
      type: 'unsubscribe',
      symbol
    }
    console.log('Sending unsubscribe message:', message)
    this.sendMessage(message)
  }

  private sendMessage(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      // Queue message for when connection is established
      this.messageQueue.push(message)
    }
  }

  private processMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()
      this.sendMessage(message)
    }
  }

  private handleMessage(message: WebSocketMessage) {
    console.log('WebSocket message received:', message.type, message)
    switch (message.type) {
      case 'orderbook':
        this.emit('orderbook', message as OrderBookMessage)
        break
      case 'error':
        this.emit('error', { error: message.error })
        console.error('WebSocket server error:', message.error)
        break
      default:
        console.log('Unknown message type:', message.type, message)
    }
  }

  private scheduleReconnect(token: string) {
    this.reconnectAttempts++
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`)
    
    setTimeout(() => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.connect(token).catch(console.error)
      }
    }, delay)
  }

  // Event system for components to listen to WebSocket events
  on(event: string, callback: (data: any) => void) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, [])
    }
    this.eventListeners.get(event)!.push(callback)
  }

  off(event: string, callback: (data: any) => void) {
    const listeners = this.eventListeners.get(event)
    if (listeners) {
      const index = listeners.indexOf(callback)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }

  private emit(event: string, data: any) {
    const listeners = this.eventListeners.get(event)
    if (listeners) {
      listeners.forEach(callback => callback(data))
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get connectionState(): string {
    if (!this.ws) return 'disconnected'
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting'
      case WebSocket.OPEN: return 'connected'
      case WebSocket.CLOSING: return 'closing'
      case WebSocket.CLOSED: return 'disconnected'
      default: return 'unknown'
    }
  }
}

