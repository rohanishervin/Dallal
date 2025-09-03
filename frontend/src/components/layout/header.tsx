'use client'

import { useMarketStore } from '@/store/market'
import { useAuthStore } from '@/store/auth'
import { Search, Bell, ChevronDown } from 'lucide-react'
import { formatPrice } from '@/lib/utils'

export function Header() {
  const { 
    selectedSymbol, 
    setSelectedSymbol,
    instruments 
  } = useMarketStore()
  
  const { sessionStatus } = useAuthStore()

  const selectedInstrument = instruments.find(inst => inst.symbol === selectedSymbol)

  return (
    <div className="h-16 bg-gray-900 border-b border-gray-700 px-6 flex items-center justify-between">
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-4">
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="bg-gray-800 border border-gray-600 text-white px-3 py-2 rounded-lg focus:outline-none focus:border-blue-500"
          >
            {instruments.map((instrument) => (
              <option key={instrument.symbol} value={instrument.symbol}>
                {instrument.symbol}
              </option>
            ))}
          </select>

          {selectedInstrument && (
            <div className="flex items-center space-x-4 text-sm">
              <div className="text-white font-medium">
                {formatPrice(1.0856, parseInt(selectedInstrument.px_precision))}
              </div>
              <div className="text-green-400">
                +0.0012 (+0.11%)
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search symbols..."
            className="bg-gray-800 border border-gray-600 text-white pl-10 pr-4 py-2 rounded-lg text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        <button className="p-2 text-gray-400 hover:text-white">
          <Bell size={18} />
        </button>

        <div className="flex items-center space-x-2">
          <div className="text-right">
            <div className="text-white text-sm font-medium">
              {sessionStatus?.session.user_id || 'User'}
            </div>
            <div className="text-gray-400 text-xs">
              {sessionStatus?.session.overall_active ? 'Online' : 'Offline'}
            </div>
          </div>
          <ChevronDown size={16} className="text-gray-400" />
        </div>
      </div>
    </div>
  )
}

