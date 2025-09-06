import { create } from 'zustand'
import { WebSocketService, OrderBookData } from '@/services/websocket'
import { config } from '@/config/env'

interface WebSocketState {
  wsService: WebSocketService | null
  orderBookData: Record<string, OrderBookData>
  lastUpdate: number
  isConnected: boolean
  connectionError: string | null
  currentSymbol: string | null
  
  connect: (token: string) => Promise<void>
  disconnect: () => void
  subscribeToSymbol: (symbol: string, levels?: number) => void
  unsubscribeFromSymbol: (symbol: string) => void
  getOrderBookForSymbol: (symbol: string) => OrderBookData | null
  clearError: () => void
}

export const useWebSocketStore = create<WebSocketState>((set, get) => {
  let wsService: WebSocketService | null = null

  return {
    wsService: null,
    orderBookData: {},
    lastUpdate: 0,
    isConnected: false,
    connectionError: null,
    currentSymbol: null,

    connect: async (token: string) => {
      const state = get()
      
      if (state.wsService?.isConnected) {
        return
      }

      try {
        if (wsService) {
          wsService.disconnect()
        }

        wsService = new WebSocketService(config.wsUrl)
        
        // Set up event listeners
        wsService.on('connected', () => {
          set({ 
            isConnected: true, 
            connectionError: null 
          })
          
          // Subscribe to current selected symbol when connected
          setTimeout(() => {
            const marketStore = require('./market').useMarketStore.getState()
            const currentSelectedSymbol = marketStore.selectedSymbol
            if (currentSelectedSymbol) {
              console.log(`WebSocket connected: Subscribing to current selected symbol: ${currentSelectedSymbol}`)
              wsService?.subscribe(currentSelectedSymbol, 5)
              set({ currentSymbol: currentSelectedSymbol })
            }
          }, 500) // Small delay to ensure connection is stable
        })

        wsService.on('disconnected', () => {
          set({ 
            isConnected: false,
            orderBookData: {},
            lastUpdate: 0,
            currentSymbol: null
          })
        })

        wsService.on('error', (error) => {
          set({ 
            connectionError: error?.error || 'Connection error',
            isConnected: false 
          })
        })

        wsService.on('orderbook', (message) => {
          const orderBookData = message.data
          console.log('Received orderbook data:', orderBookData.symbol, orderBookData)
          set((state) => ({
            orderBookData: {
              ...state.orderBookData,
              [orderBookData.symbol]: orderBookData
            },
            lastUpdate: Date.now(),
            connectionError: null // Clear any previous connection errors when we receive data
          }))
        })

        await wsService.connect(token)
        
        set({ 
          wsService,
          connectionError: null 
        })
        
      } catch (error) {
        console.error('Failed to connect WebSocket:', error)
        set({ 
          connectionError: error instanceof Error ? error.message : 'Connection failed',
          isConnected: false 
        })
        throw error
      }
    },

    disconnect: () => {
      if (wsService) {
        wsService.disconnect()
        wsService = null
      }
      
      set({
        wsService: null,
        isConnected: false,
        orderBookData: {},
        lastUpdate: 0,
        currentSymbol: null,
        connectionError: null
      })
    },

    subscribeToSymbol: (symbol: string, levels = 5) => {
      const state = get()
      
      if (!state.wsService || !state.wsService.isConnected) {
        set({ connectionError: 'WebSocket not connected' })
        return
      }

      // Clear any previous connection errors when attempting new subscription
      set({ connectionError: null })

      // If switching to a different symbol, unsubscribe from current first
      if (state.currentSymbol && state.currentSymbol !== symbol) {
        console.log(`Unsubscribing from ${state.currentSymbol}`)
        state.wsService.unsubscribe(state.currentSymbol)
        
        // Clear the old symbol's data
        set((state) => {
          const newData = { ...state.orderBookData }
          delete newData[state.currentSymbol!]
          return { orderBookData: newData }
        })
      }

      // Subscribe to new symbol - preserve exact case
      console.log(`Subscribing to symbol: "${symbol}" (exact case preserved)`)
      state.wsService.subscribe(symbol, levels)
      set({ currentSymbol: symbol })
    },

    unsubscribeFromSymbol: (symbol: string) => {
      const state = get()
      
      if (!state.wsService || !state.wsService.isConnected) {
        return
      }

      state.wsService.unsubscribe(symbol)
      
      set((state) => {
        const newData = { ...state.orderBookData }
        delete newData[symbol]
        return { 
          orderBookData: newData,
          currentSymbol: state.currentSymbol === symbol ? null : state.currentSymbol
        }
      })
    },

    getOrderBookForSymbol: (symbol: string) => {
      const state = get()
      return state.orderBookData[symbol] || null
    },

    clearError: () => {
      set({ connectionError: null })
    }
  }
})

// Auto-connect when token is available
if (typeof window !== 'undefined') {
  const token = localStorage.getItem('auth_token')
  if (token) {
    console.log('Auto-connecting WebSocket with token')
    useWebSocketStore.getState().connect(token).catch(console.error)
  }
}