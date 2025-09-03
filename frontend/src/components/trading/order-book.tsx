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
  ],
  asks: [
    { price: 1.08565, size: 1.9 },
    { price: 1.08570, size: 2.3 },
    { price: 1.08575, size: 1.6 },
    { price: 1.08580, size: 2.7 },
    { price: 1.08585, size: 1.1 },
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
      <div className="w-full bg-gray-900 rounded-lg border border-gray-700">
        <div className="p-3 border-b border-gray-700">
          <h3 className="text-white font-medium text-sm">Order Book</h3>
        </div>
        <div className="p-3 flex items-center justify-center h-20">
          <div className="text-gray-400 text-xs">Loading...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full bg-gray-900 rounded-lg border border-gray-700 flex flex-col max-h-80">
      <div className="p-3 border-b border-gray-700 flex-shrink-0">
        <h3 className="text-white font-medium text-sm">Order Book</h3>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
        <div className="p-3">
          <div className="grid grid-cols-2 text-xs text-gray-400 mb-2 sticky top-0 bg-gray-900 z-10">
            <div>Price</div>
            <div className="text-right">Size</div>
          </div>

          {/* Asks (sell orders) - shown in reverse order */}
          <div className="space-y-0.5 mb-2">
            {[...orderBook.asks].reverse().map((ask, index) => (
              <div key={`ask-${index}`} className="grid grid-cols-2 text-xs hover:bg-gray-800 px-1 py-0.5 rounded">
                <div className="text-red-400 font-mono">
                  {formatPrice(ask.price, 5)}
                </div>
                <div className="text-right text-gray-300 font-mono">
                  {ask.size.toFixed(1)}
                </div>
              </div>
            ))}
          </div>

          {/* Current price spread */}
          <div className="border-t border-b border-gray-700 py-1.5 mb-2 sticky top-6 bg-gray-900 z-10">
            <div className="text-center text-white font-mono text-xs">
              1.08562
            </div>
            <div className="text-center text-xs text-gray-400">
              Spread: 0.00002
            </div>
          </div>

          {/* Bids (buy orders) */}
          <div className="space-y-0.5">
            {orderBook.bids.map((bid, index) => (
              <div key={`bid-${index}`} className="grid grid-cols-2 text-xs hover:bg-gray-800 px-1 py-0.5 rounded">
                <div className="text-green-400 font-mono">
                  {formatPrice(bid.price, 5)}
                </div>
                <div className="text-right text-gray-300 font-mono">
                  {bid.size.toFixed(1)}
                </div>
              </div>
            ))}
            
            {/* Add more mock data to demonstrate scrolling */}
            {Array.from({ length: 15 }, (_, i) => (
              <div key={`extra-bid-${i}`} className="grid grid-cols-2 text-xs hover:bg-gray-800 px-1 py-0.5 rounded">
                <div className="text-green-400 font-mono">
                  {formatPrice(1.08530 - (i * 0.00005), 5)}
                </div>
                <div className="text-right text-gray-300 font-mono">
                  {(Math.random() * 3 + 0.5).toFixed(1)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

