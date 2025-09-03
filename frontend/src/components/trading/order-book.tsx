'use client'

import { useState, useEffect } from 'react'
import { formatPrice } from '@/lib/utils'

const getMockOrderBook = () => ({
  bids: [
    { price: 1.08560, size: 2.5 },
    { price: 1.08555, size: 1.8 },
    { price: 1.08550, size: 3.2 },
    { price: 1.08545, size: 0.9 },
    { price: 1.08540, size: 2.1 },
    { price: 1.08535, size: 1.5 },
    { price: 1.08530, size: 2.8 },
    { price: 1.08525, size: 1.2 },
  ],
  asks: [
    { price: 1.08565, size: 1.9 },
    { price: 1.08570, size: 2.3 },
    { price: 1.08575, size: 1.6 },
    { price: 1.08580, size: 2.7 },
    { price: 1.08585, size: 1.1 },
    { price: 1.08590, size: 2.4 },
    { price: 1.08595, size: 1.8 },
    { price: 1.08600, size: 3.0 },
  ]
})

export function OrderBook() {
  const [mounted, setMounted] = useState(false)
  const [orderBook, setOrderBook] = useState<ReturnType<typeof getMockOrderBook> | null>(null)

  useEffect(() => {
    setMounted(true)
    setOrderBook(getMockOrderBook())
  }, [])

  if (!mounted || !orderBook) {
    return (
      <div className="w-80 bg-gray-900 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-white font-medium">Order Book</h3>
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
        <h3 className="text-white font-medium">Order Book</h3>
      </div>

      <div className="p-4">
        <div className="grid grid-cols-2 text-xs text-gray-400 mb-2">
          <div>Price</div>
          <div className="text-right">Size</div>
        </div>

        <div className="space-y-1 mb-4">
          {[...orderBook.asks].reverse().map((ask, index) => (
            <div key={`ask-${index}`} className="grid grid-cols-2 text-xs">
              <div className="text-red-400 font-mono">
                {formatPrice(ask.price, 5)}
              </div>
              <div className="text-right text-gray-300 font-mono">
                {ask.size.toFixed(1)}
              </div>
            </div>
          ))}
        </div>

        <div className="border-t border-b border-gray-700 py-2 mb-4">
          <div className="text-center text-white font-mono text-sm">
            1.08562
          </div>
          <div className="text-center text-xs text-gray-400">
            Spread: 0.00002
          </div>
        </div>

        <div className="space-y-1">
          {orderBook.bids.map((bid, index) => (
            <div key={`bid-${index}`} className="grid grid-cols-2 text-xs">
              <div className="text-green-400 font-mono">
                {formatPrice(bid.price, 5)}
              </div>
              <div className="text-right text-gray-300 font-mono">
                {bid.size.toFixed(1)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

