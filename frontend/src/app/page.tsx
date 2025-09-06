'use client'

import { useEffect } from 'react'
import { Header } from '@/components/layout/header'
import { PriceChart } from '@/components/trading/price-chart'
import { MarketWatch } from '@/components/trading/market-watch'
import { OrderBook } from '@/components/trading/order-book'
import { TradePanel } from '@/components/trading/trade-panel'
import { LoginModal } from '@/components/auth/login-modal'
import { useAuthStore } from '@/store/auth'
import { useMarketStore } from '@/store/market'
import { useWebSocketStore } from '@/store/websocket'
import { apiClient } from '@/lib/api'
import { WebSocketDebugPanel } from '@/components/debug/websocket-status'

export default function TradingDashboard() {
  const { isAuthenticated, sessionStatus, checkSession } = useAuthStore()
  const { loadInstruments, selectedSymbol } = useMarketStore()
  const { connect, disconnect, subscribeToSymbol, isConnected } = useWebSocketStore()

  // Initial session check
  useEffect(() => {
    checkSession()
  }, [checkSession])

  // Load instruments when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadInstruments()
    }
  }, [isAuthenticated, loadInstruments])

  // Handle WebSocket connection lifecycle
  useEffect(() => {
    const connectWebSocket = async () => {
      // Only connect if:
      // 1. User is authenticated
      // 2. Session status shows healthy trade and feed sessions
      // 3. WebSocket is not already connected
      if (
        isAuthenticated && 
        sessionStatus?.success && 
        sessionStatus.session?.overall_active &&
        sessionStatus.session?.trade_session?.is_active &&
        sessionStatus.session?.feed_session?.is_active &&
        !isConnected
      ) {
        const token = apiClient['token']
        if (token) {
          try {
            console.log('Connecting to WebSocket...')
            await connect(token)
            console.log('WebSocket connected successfully')
            // Subscribe to default symbol if available
            if (selectedSymbol) {
              console.log(`Subscribing to ${selectedSymbol}`)
              subscribeToSymbol(selectedSymbol, 5)
            }
          } catch (error) {
            console.error('WebSocket connection error:', error)
          }
        }
      }
    }

    connectWebSocket()

    // Cleanup on logout
    return () => {
      if (!isAuthenticated && isConnected) {
        disconnect()
      }
    }
  }, [isAuthenticated, sessionStatus, selectedSymbol, isConnected, connect, disconnect, subscribeToSymbol])

  // Handle symbol changes for WebSocket subscription
  useEffect(() => {
    if (isConnected && selectedSymbol) {
      console.log(`Switching WebSocket subscription to ${selectedSymbol}`)
      subscribeToSymbol(selectedSymbol, 5)
    }
  }, [selectedSymbol, isConnected, subscribeToSymbol])

  return (
    <div className="h-screen bg-black flex flex-col overflow-hidden">
      <LoginModal isOpen={!isAuthenticated} />
      
      <div className={`flex-1 flex flex-col min-h-0 ${!isAuthenticated ? 'blur-sm' : ''}`}>
        <Header />
        
        {/* Main trading area - fills remaining viewport */}
        <div className="flex-1 min-h-0 flex overflow-hidden">
          {/* Left panel - Trade Panel - Fixed 20% width */}
          <div className="w-1/5 flex-shrink-0 p-4 pr-2">
            <TradePanel />
          </div>
          
          {/* Center panel - Chart only (flexible) */}
          <div className="flex-1 min-w-0 p-4 px-2">
            <PriceChart />
          </div>
          
          {/* Right panel - Market Watch and Order Book - Fixed 20% width */}
          <div className="w-1/5 flex-shrink-0 p-4 pl-2 flex flex-col min-h-0">
            <div className="flex-1 min-h-0 mb-4">
              <MarketWatch />
            </div>
            <div className="flex-shrink-0">
              <OrderBook />
            </div>
          </div>
        </div>

        {/* Debug WebSocket Status - Remove in production */}
        {/* <WebSocketDebugPanel /> */}

        {/* Trigger area for bottom section */}
        <div className="bottom-section-trigger"></div>

        {/* Bottom section - Positions & Orders (appears on scroll down) */}
        <div className="h-0 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-900 group hover:h-80 focus-within:h-80 transition-all duration-500 ease-in-out bg-gray-950 border-t border-gray-800">
          <div className="min-h-80 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-medium">Positions & Orders</h3>
              <div className="text-xs text-gray-400 opacity-60">
                ↑ Hover to expand ↑
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              {/* Positions */}
              <div className="bg-gray-900 rounded-lg p-3">
                <h4 className="text-white font-medium text-sm mb-3">Open Positions</h4>
                <div className="space-y-2">
                  {Array.from({ length: 5 }, (_, i) => (
                    <div key={i} className="p-2 bg-gray-800 rounded text-xs text-gray-300 hover:bg-gray-700 transition-colors">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium">EUR/USD</span>
                        <span className={i % 2 === 0 ? "text-green-400" : "text-red-400"}>
                          {i % 2 === 0 ? "LONG" : "SHORT"}
                        </span>
                      </div>
                      <div className="flex justify-between text-gray-400">
                        <span>{(Math.random() * 2 + 0.5).toFixed(2)} lots</span>
                        <span>{i % 2 === 0 ? "+$" : "-$"}{(Math.random() * 500 + 50).toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Orders */}
              <div className="bg-gray-900 rounded-lg p-3">
                <h4 className="text-white font-medium text-sm mb-3">Pending Orders</h4>
                <div className="space-y-2">
                  {Array.from({ length: 3 }, (_, i) => (
                    <div key={i} className="p-2 bg-gray-800 rounded text-xs text-gray-300 hover:bg-gray-700 transition-colors">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium">GBP/USD</span>
                        <span className="text-gray-400">PENDING</span>
                      </div>
                      <div className="flex justify-between text-gray-400">
                        <span>{(Math.random() * 1 + 0.5).toFixed(2)} lots</span>
                        <span>@ {(1.25 + Math.random() * 0.1).toFixed(5)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}