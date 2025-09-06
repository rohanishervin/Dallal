'use client'

import { useState, useEffect } from 'react'
import { useMarketStore } from '@/store/market'
import { Search } from 'lucide-react'

export function MarketWatch() {
  const { instruments, selectedSymbol, setSelectedSymbol } = useMarketStore()
  const [mounted, setMounted] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    setMounted(true)
  }, [])

  const tradeEnabledInstruments = instruments.filter(instrument => instrument.trade_enabled)
  
  const filteredInstruments = tradeEnabledInstruments.filter(instrument => {
    const normalizedSearchTerm = searchTerm.toLowerCase().replace(/[^a-z0-9]/g, '')
    const normalizedSymbol = instrument.symbol.toLowerCase().replace(/[^a-z0-9]/g, '')
    const normalizedDescription = instrument.description ? 
      instrument.description.toLowerCase().replace(/[^a-z0-9]/g, '') : ''
    
    return normalizedSymbol.includes(normalizedSearchTerm) ||
           normalizedDescription.includes(normalizedSearchTerm) ||
           instrument.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
           (instrument.description && instrument.description.toLowerCase().includes(searchTerm.toLowerCase()))
  })

  if (!mounted) {
    return (
      <div className="w-full h-full bg-gray-900 rounded-lg border border-gray-700">
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
        <div className="relative">
          <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Search instruments..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 text-white px-8 py-1.5 rounded text-xs focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
        <div className="grid grid-cols-4 gap-2 p-2 text-xs text-gray-400 border-b border-gray-800 sticky top-0 bg-gray-900">
          <div className="font-medium">Symbol</div>
          <div className="font-medium">Description</div>
          <div className="font-medium">Contract Size</div>
          <div className="font-medium">Precision</div>
        </div>
        
        {filteredInstruments.map((instrument) => {
          const isSelected = instrument.symbol === selectedSymbol

          return (
            <button
              key={instrument.symbol}
              onClick={() => setSelectedSymbol(instrument.symbol)}
              className={`w-full p-2 border-b border-gray-800 hover:bg-gray-800 transition-colors text-left ${
                isSelected ? 'bg-blue-900/20 border-blue-700' : ''
              }`}
            >
              <div className="grid grid-cols-4 gap-2 text-xs">
                <div className="text-white font-medium truncate">
                  {instrument.symbol}
                </div>
                <div className="text-gray-300 truncate">
                  {instrument.description || 'No description'}
                </div>
                <div className="text-gray-300 text-right">
                  {instrument.round_lot}
                </div>
                <div className="text-gray-300 text-right">
                  {instrument.px_precision}
                </div>
              </div>
            </button>
          )
        })}
        
        {filteredInstruments.length === 0 && (
          <div className="p-4 text-center text-gray-400 text-sm">
            No instruments found
          </div>
        )}
      </div>
    </div>
  )
}

