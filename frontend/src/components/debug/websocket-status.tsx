'use client'

import { useState, useEffect } from 'react'
import { useWebSocketStore } from '@/store/websocket'
import { useMarketStore } from '@/store/market'

export function WebSocketDebugPanel() {
  const [messages, setMessages] = useState<string[]>([])
  const { isConnected, currentSymbol, connectionError } = useWebSocketStore()
  const { selectedSymbol, setSelectedSymbol } = useMarketStore()

  const addMessage = (message: string) => {
    setMessages(prev => [...prev.slice(-9), `${new Date().toLocaleTimeString()}: ${message}`])
  }

  useEffect(() => {
    addMessage(`WebSocket ${isConnected ? 'Connected' : 'Disconnected'}`)
  }, [isConnected])

  useEffect(() => {
    if (currentSymbol) {
      addMessage(`Subscribed to ${currentSymbol}`)
    }
  }, [currentSymbol])

  useEffect(() => {
    if (connectionError) {
      addMessage(`Error: ${connectionError}`)
    }
  }, [connectionError])

  const testSymbols = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD']

  return (
    <div className="bg-gray-800 border border-gray-600 rounded-lg p-4 text-sm">
      <h3 className="text-white font-medium mb-3">WebSocket Debug Panel</h3>
      
      <div className="space-y-2 mb-4">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
          <span className="text-gray-300">
            Status: {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        
        <div className="text-gray-300">
          Current Symbol: <span className="text-white">{currentSymbol || 'None'}</span>
        </div>
        
        <div className="text-gray-300">
          Selected Symbol: <span className="text-white">{selectedSymbol}</span>
        </div>
      </div>

      <div className="mb-4">
        <h4 className="text-gray-300 text-xs mb-2">Test Symbol Switching:</h4>
        <div className="flex flex-wrap gap-2">
          {testSymbols.map(symbol => (
            <button
              key={symbol}
              onClick={() => setSelectedSymbol(symbol)}
              className={`px-2 py-1 text-xs rounded ${
                selectedSymbol === symbol 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {symbol}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h4 className="text-gray-300 text-xs mb-2">Recent Messages:</h4>
        <div className="bg-gray-900 rounded p-2 h-32 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="text-gray-500 text-xs">No messages yet...</div>
          ) : (
            messages.map((msg, index) => (
              <div key={index} className="text-xs text-gray-400 font-mono">
                {msg}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}