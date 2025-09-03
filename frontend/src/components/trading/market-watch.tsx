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
    <div className="w-80 bg-gray-900 rounded-lg border border-gray-700">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-white font-medium">Market Watch</h3>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {topInstruments.map((instrument) => {
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
                <div>
                  <div className="text-white font-medium text-sm">
                    {instrument.symbol}
                  </div>
                  <div className="text-gray-400 text-xs">
                    {instrument.description}
                  </div>
                </div>
                
                <div className="text-right">
                  <div className="text-white font-mono text-sm">
                    {formatPrice(mockData.price, parseInt(instrument.px_precision))}
                  </div>
                  <div className={`flex items-center text-xs ${
                    isPositive ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {isPositive ? (
                      <TrendingUp size={12} className="mr-1" />
                    ) : (
                      <TrendingDown size={12} className="mr-1" />
                    )}
                    {isPositive ? '+' : ''}{mockData.change.toFixed(4)} ({isPositive ? '+' : ''}{mockData.changePercent.toFixed(2)}%)
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

