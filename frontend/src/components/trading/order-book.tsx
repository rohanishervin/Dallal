'use client'

import { useState, useEffect } from 'react'
import { formatPrice } from '@/lib/utils'
import { useWebSocketStore } from '@/store/websocket'
import { useMarketStore } from '@/store/market'
import type { OrderBookData } from '@/services/websocket'

export function OrderBook() {
  const [mounted, setMounted] = useState(false)
  const { selectedSymbol } = useMarketStore()
  const { orderBookData, isConnected, connectionError, getOrderBookForSymbol, lastUpdate } = useWebSocketStore()
  const [currentOrderBook, setCurrentOrderBook] = useState<OrderBookData | null>(null)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Update orderbook when data changes for selected symbol
  useEffect(() => {
    if (selectedSymbol) {
      const orderBook = getOrderBookForSymbol(selectedSymbol)
      setCurrentOrderBook(orderBook)
      
      // Subscribe to the selected symbol if WebSocket is connected
      if (isConnected && selectedSymbol) {
        const { subscribeToSymbol } = useWebSocketStore.getState()
        subscribeToSymbol(selectedSymbol, 5)
      }
    }
  }, [selectedSymbol, orderBookData, getOrderBookForSymbol, isConnected])

  // Listen for real-time orderbook updates
  useEffect(() => {
    if (selectedSymbol) {
      const orderBook = getOrderBookForSymbol(selectedSymbol)
      if (orderBook) {
        setCurrentOrderBook(orderBook)
        console.log(`OrderBook updated for ${selectedSymbol}:`, {
          symbol: orderBook.symbol,
          bidsCount: orderBook.bids.length,
          asksCount: orderBook.asks.length,
          bids: orderBook.bids.slice(0, 3),
          asks: orderBook.asks.slice(0, 3)
        })
      }
    }
  }, [orderBookData, selectedSymbol, getOrderBookForSymbol, lastUpdate])

  if (!mounted) {
    return (
      <div className="w-full bg-gray-900 border border-gray-700">
        <div className="p-3 border-b border-gray-700">
          <h3 className="text-white font-medium text-sm">Order Book</h3>
        </div>
        <div className="p-3 flex items-center justify-center h-20">
          <div className="text-gray-400 text-xs">Loading...</div>
        </div>
      </div>
    )
  }

  // Show connection status if not connected
  if (!isConnected) {
    return (
      <div className="w-full bg-gray-900 border border-gray-700">
        <div className="p-3 border-b border-gray-700">
          <h3 className="text-white font-medium text-sm">Order Book</h3>
        </div>
        <div className="p-3 flex items-center justify-center h-20">
          <div className="text-center">
            <div className="text-red-400 text-xs mb-1">
              {connectionError ? 'Connection Error' : 'Disconnected'}
            </div>
            {connectionError && (
              <div className="text-gray-400 text-xs">{connectionError}</div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Show waiting for data if connected but no orderbook data
  if (!currentOrderBook) {
    return (
      <div className="w-full bg-gray-900 border border-gray-700">
        <div className="p-3 border-b border-gray-700">
          <h3 className="text-white font-medium text-sm">Order Book</h3>
        </div>
        <div className="p-3 flex items-center justify-center h-20">
          <div className="text-center">
            <div className="text-yellow-400 text-xs mb-1">Connected</div>
            <div className="text-gray-400 text-xs">Waiting for {selectedSymbol} data...</div>
          </div>
        </div>
      </div>
    )
  }

  // Calculate precision from the symbol's instrument data
  const getPricePrecision = (symbol: string) => {
    // Default precision, could be enhanced by fetching from instruments data
    return 5
  }

  const formatPriceWithCommas = (price: number, precision: number) => {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: precision,
      maximumFractionDigits: precision
    })
  }

  const formatSize = (size: number) => {
    if (size >= 1000000) {
      return `${(size / 1000000).toFixed(2)}M`
    } else if (size >= 1000) {
      return `${(size / 1000).toFixed(2)}K`
    } else if (size >= 1) {
      return `${size.toFixed(5)}`
    } else {
      return `${size.toFixed(8)}`
    }
  }

  const formatTotal = (total: number) => {
    if (total >= 1000000) {
      return `${(total / 1000000).toFixed(2)}M`
    } else if (total >= 1000) {
      return `${(total / 1000).toFixed(2)}K`
    } else {
      return `${total.toFixed(2)}`
    }
  }

  // Get exactly 5 levels for each side, sorted properly with cumulative totals
  const getTopAsks = () => {
    const asks = [...currentOrderBook.asks]
      .sort((a, b) => b.price - a.price) // Sort descending (highest ask first, like in the image)
      .slice(0, 5)
    
    // Calculate cumulative totals
    let cumulativeTotal = 0
    return asks.map((ask, index) => {
      cumulativeTotal += ask.size * ask.price
      return {
        ...ask,
        cumulativeTotal
      }
    })
  }

  const getTopBids = () => {
    const bids = [...currentOrderBook.bids]
      .sort((a, b) => b.price - a.price) // Sort descending (highest bid first)
      .slice(0, 5)
    
    // Calculate cumulative totals
    let cumulativeTotal = 0
    return bids.map((bid, index) => {
      cumulativeTotal += bid.size * bid.price
      return {
        ...bid,
        cumulativeTotal
      }
    })
  }

  const topAsks = getTopAsks()
  const topBids = getTopBids()
  const maxTotal = Math.max(
    ...topAsks.map(ask => ask.cumulativeTotal),
    ...topBids.map(bid => bid.cumulativeTotal)
  )

  console.log('OrderBook levels:', {
    asksCount: topAsks.length,
    bidsCount: topBids.length,
    maxTotal,
    topAsks: topAsks.map(a => ({ price: a.price, size: a.size, total: a.cumulativeTotal })),
    topBids: topBids.map(b => ({ price: b.price, size: b.size, total: b.cumulativeTotal }))
  })

  const pricePrecision = getPricePrecision(currentOrderBook.symbol)

  return (
    <div className="w-full bg-gray-900 border border-gray-700 flex flex-col h-96">
      <div className="p-3 border-b border-gray-700 flex-shrink-0 bg-gray-900">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold text-sm">Order Book</h3>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-400 animate-pulse"></div>
            <span className="text-xs text-gray-300 font-mono">{currentOrderBook.symbol}</span>
            {lastUpdate > 0 && (
              <span className="text-xs text-gray-500 font-mono">
                {new Date(lastUpdate).toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-2 text-xs text-gray-400 px-3 py-2 border-b border-gray-700 bg-gray-800">
          <div className="text-left">Price</div>
          <div className="text-right">Amount</div>
        </div>

        {/* Asks Section - Red theme */}
        <div className="space-y-0">
          {topAsks.map((ask, index) => {
            const sizePercentage = ask.size > 0 ? (ask.size / Math.max(...topAsks.map(a => a.size), ...topBids.map(b => b.size))) * 100 : 0
            return (
              <div key={`ask-${index}`} className="relative grid grid-cols-2 text-xs py-1 px-3 hover:bg-red-900/10">
                {/* Size bar background - red, right-aligned */}
                {ask.size > 0 && (
                  <div className="absolute inset-0 bg-red-900/20" 
                       style={{ width: `${sizePercentage}%`, right: 0 }}></div>
                )}
                
                {/* Content */}
                <div className="relative text-left text-red-400 font-mono">
                  {ask.price > 0 ? formatPriceWithCommas(ask.price, pricePrecision) : '-'}
                </div>
                <div className="relative text-right text-white font-mono">
                  {ask.size > 0 ? formatSize(ask.size) : '-'}
                </div>
              </div>
            )
          })}
        </div>

        {/* Spread Section */}
        <div className="bg-gray-800 border-t border-b border-gray-600 py-2">
          <div className="text-center text-white font-mono text-xs">
            {formatPriceWithCommas(currentOrderBook.best_ask, pricePrecision)} - {formatPriceWithCommas(currentOrderBook.best_bid, pricePrecision)} = {formatPriceWithCommas(currentOrderBook.spread, pricePrecision)}
          </div>
        </div>

        {/* Bids Section - Green theme */}
        <div className="space-y-0">
          {topBids.map((bid, index) => {
            const sizePercentage = bid.size > 0 ? (bid.size / Math.max(...topAsks.map(a => a.size), ...topBids.map(b => b.size))) * 100 : 0
            return (
              <div key={`bid-${index}`} className="relative grid grid-cols-2 text-xs py-1 px-3 hover:bg-green-900/10">
                {/* Size bar background - green, left-aligned */}
                {bid.size > 0 && (
                  <div className="absolute inset-0 bg-green-900/20" 
                       style={{ width: `${sizePercentage}%`, left: 0 }}></div>
                )}
                
                {/* Content */}
                <div className="relative text-left text-green-400 font-mono">
                  {bid.price > 0 ? formatPriceWithCommas(bid.price, pricePrecision) : '-'}
                </div>
                <div className="relative text-right text-white font-mono">
                  {bid.size > 0 ? formatSize(bid.size) : '-'}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Footer with metadata */}
      <div className="p-2 border-t border-gray-700 flex-shrink-0 bg-gray-900">
        <div className="flex justify-between text-xs text-gray-400 font-mono">
          <span>Depth: 5</span>
          <span>
            Last: {new Date(currentOrderBook.timestamp).toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  )
}

