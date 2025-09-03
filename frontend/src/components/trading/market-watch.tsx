'use client'

import { useState, useEffect } from 'react'
import { useMarketStore } from '@/store/market'
import { formatPrice } from '@/lib/utils'
import { TrendingUp, TrendingDown } from 'lucide-react'

const getMockPrices = () => ({
  'EUR/USD': { price: 1.0856, change: 0.0012, changePercent: 0.11 },
  'GBP/USD': { price: 1.2634, change: -0.0023, changePercent: -0.18 },
  'USD/JPY': { price: 148.45, change: 0.34, changePercent: 0.23 },
  'AUD/USD': { price: 0.6789, change: 0.0045, changePercent: 0.67 },
  'USD/CHF': { price: 0.8923, change: -0.0012, changePercent: -0.13 },
})

export function MarketWatch() {
  const { instruments, selectedSymbol, setSelectedSymbol } = useMarketStore()
  const [mounted, setMounted] = useState(false)
  const [mockPrices, setMockPrices] = useState<ReturnType<typeof getMockPrices> | null>(null)

  useEffect(() => {
    setMounted(true)
    setMockPrices(getMockPrices())
  }, [])

  const topInstruments = instruments.slice(0, 8)

  if (!mounted || !mockPrices) {
    return (
      <div className="w-80 bg-gray-900 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-white font-medium">Market Watch</h3>
        </div>
        <div className="p-4 flex items-center justify-center h-32">
          <div className="text-gray-400 text-sm">Loading...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full h-full bg-gray-900 rounded-lg border border-gray-700 flex flex-col">
      <div className="p-3 border-b border-gray-700 flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-white font-medium text-sm">Market Watch</h3>
        </div>
        <select
          value={selectedSymbol}
          onChange={(e) => setSelectedSymbol(e.target.value)}
          className="w-full bg-gray-800 border border-gray-600 text-white px-2 py-1.5 rounded text-xs focus:outline-none focus:border-blue-500"
        >
          {instruments.map((instrument) => (
            <option key={instrument.symbol} value={instrument.symbol}>
              {instrument.symbol} - {instrument.description}
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
        {instruments.slice(0, 12).map((instrument) => {
          const mockData = mockPrices[instrument.symbol as keyof typeof mockPrices] || {
            price: 1.0000,
            change: 0,
            changePercent: 0
          }
          
          const isSelected = instrument.symbol === selectedSymbol
          const isPositive = mockData.change >= 0

          return (
            <button
              key={instrument.symbol}
              onClick={() => setSelectedSymbol(instrument.symbol)}
              className={`w-full p-3 border-b border-gray-800 hover:bg-gray-800 transition-colors text-left ${
                isSelected ? 'bg-blue-900/20 border-blue-700' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="text-white font-medium text-sm truncate">
                    {instrument.symbol}
                  </div>
                  <div className="text-gray-400 text-xs truncate">
                    {instrument.description || 'No description'}
                  </div>
                </div>
                
                <div className="text-right ml-2 flex-shrink-0">
                  <div className="text-white font-mono text-sm">
                    {formatPrice(mockData.price, parseInt(instrument.px_precision || '5'))}
                  </div>
                  <div className={`flex items-center text-xs ${
                    isPositive ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {isPositive ? (
                      <TrendingUp size={12} className="mr-1" />
                    ) : (
                      <TrendingDown size={12} className="mr-1" />
                    )}
                    <span>
                      {isPositive ? '+' : ''}{mockData.change.toFixed(4)} ({isPositive ? '+' : ''}{mockData.changePercent.toFixed(2)}%)
                    </span>
                  </div>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

