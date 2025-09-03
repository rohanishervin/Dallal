'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useMarketStore } from '@/store/market'

export function TradePanel() {
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market')
  const [side, setSide] = useState<'buy' | 'sell'>('buy')
  const [amount, setAmount] = useState('')
  const [price, setPrice] = useState('')
  
  const { selectedSymbol } = useMarketStore()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Order submitted:', { orderType, side, amount, price, symbol: selectedSymbol })
  }

  return (
    <div className="w-80 bg-gray-900 rounded-lg border border-gray-700">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-white font-medium">Trade</h3>
      </div>

      <form onSubmit={handleSubmit} className="p-4 space-y-4">
        <div className="flex space-x-2">
          <button
            type="button"
            onClick={() => setOrderType('market')}
            className={`flex-1 py-2 px-3 rounded text-sm font-medium transition-colors ${
              orderType === 'market'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Market
          </button>
          <button
            type="button"
            onClick={() => setOrderType('limit')}
            className={`flex-1 py-2 px-3 rounded text-sm font-medium transition-colors ${
              orderType === 'limit'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Limit
          </button>
        </div>

        <div>
          <label className="block text-sm text-gray-300 mb-2">Symbol</label>
          <div className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white">
            {selectedSymbol}
          </div>
        </div>

        <div>
          <label className="block text-sm text-gray-300 mb-2">Amount</label>
          <Input
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            className="bg-gray-800 border-gray-600 text-white"
          />
        </div>

        {orderType === 'limit' && (
          <div>
            <label className="block text-sm text-gray-300 mb-2">Price</label>
            <Input
              type="number"
              step="0.00001"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00000"
              className="bg-gray-800 border-gray-600 text-white"
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          <Button
            type="submit"
            onClick={() => setSide('buy')}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            Buy
          </Button>
          <Button
            type="submit"
            onClick={() => setSide('sell')}
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            Sell
          </Button>
        </div>

        <div className="text-xs text-gray-400 space-y-1">
          <div className="flex justify-between">
            <span>Margin Required:</span>
            <span>$0.00</span>
          </div>
          <div className="flex justify-between">
            <span>Available Balance:</span>
            <span>$10,000.00</span>
          </div>
        </div>
      </form>
    </div>
  )
}

