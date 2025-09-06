import { create } from 'zustand'
import { apiClient, type Instrument, type HistoryBar } from '@/lib/api'
import { useWebSocketStore } from './websocket'

interface MarketState {
  instruments: Instrument[]
  selectedSymbol: string
  selectedSymbolInfo: Instrument | null
  isLoadingInstruments: boolean
  isLoadingHistory: boolean
  historyBars: HistoryBar[]
  priceType: 'A' | 'B'
  loadInstruments: () => Promise<void>
  loadHistory: (symbol: string, timeframe: string, count?: number) => Promise<void>
  setSelectedSymbol: (symbol: string) => void
  setPriceType: (type: 'A' | 'B') => void
}

export const useMarketStore = create<MarketState>((set, get) => ({
  instruments: [],
  selectedSymbol: 'EUR/USD',
  selectedSymbolInfo: null,
  isLoadingInstruments: false,
  isLoadingHistory: false,
  historyBars: [],
  priceType: 'B',

  loadInstruments: async () => {
    set({ isLoadingInstruments: true })
    
    try {
      const response = await apiClient.getInstruments()
      
      if (response.success) {
        set({ instruments: response.symbols })
      } else {
        console.error('Failed to load instruments:', response.message)
      }
    } catch (error) {
      console.error('Error loading instruments:', error)
    } finally {
      set({ isLoadingInstruments: false })
    }
  },

  loadHistory: async (symbol: string, timeframe: string, count = 100) => {
    set({ isLoadingHistory: true })
    
    try {
      const response = await apiClient.getHistory({
        symbol,
        timeframe,
        count,
        price_type: get().priceType,
      })
      
      if (response.success) {
        set({ historyBars: response.bars })
      } else {
        console.error('Failed to load history:', response.message)
        set({ historyBars: [] })
      }
    } catch (error) {
      console.error('Error loading history:', error)
      set({ historyBars: [] })
    } finally {
      set({ isLoadingHistory: false })
    }
  },

  setSelectedSymbol: (symbol: string) => {
    const state = get()
    
    // Find the symbol info from instruments
    const symbolInfo = state.instruments.find(inst => inst.symbol === symbol) || null
    
    set({ 
      selectedSymbol: symbol,
      selectedSymbolInfo: symbolInfo
    })
    
    // Trigger WebSocket subscription to the new symbol
    const wsStore = useWebSocketStore.getState()
    if (wsStore.isConnected) {
      console.log(`Market store: Subscribing to ${symbol}`)
      wsStore.subscribeToSymbol(symbol, 5)
    }
  },

  setPriceType: (type: 'A' | 'B') => {
    set({ priceType: type })
  },
}))

