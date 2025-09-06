'use client'

import { useState, useEffect } from 'react'
import { formatPrice } from '@/lib/utils'
import { useWebSocketStore } from '@/store/websocket'
import { useMarketStore } from '@/store/market'
import type { OrderBookData } from '@/services/websocket'

export function OrderBook() {
  const [mounted, setMounted] = useState(false)
  const { selectedSymbol, selectedSymbolInfo } = useMarketStore()
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

  // Get precision and contract multiplier from symbol info
  const getPricePrecision = () => {
    if (selectedSymbolInfo?.px_precision) {
      return parseInt(selectedSymbolInfo.px_precision) || 5
    }
    return 5
  }
  
  const getRoundLot = () => {
    if (selectedSymbolInfo?.round_lot) {
      return parseFloat(selectedSymbolInfo.round_lot) || 1
    }
    return 1
  }

  const formatPriceWithCommas = (price: number, precision: number) => {
    return price.toFixed(precision)
  }

  const formatLots = (size: number) => {
    const roundLot = getRoundLot()
    const lots = size / roundLot
    
    if (lots >= 1000000) {
      return `${(lots / 1000000).toFixed(2)}M`
    } else if (lots >= 1000) {
      return `${(lots / 1000).toFixed(2)}K`
    } else if (lots >= 1) {
      return `${lots.toFixed(2)}`
    } else {
      return `${lots.toFixed(5)}`
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
      .sort((a, b) => a.price - b.price) // Sort ascending (lowest ask closest to spread)
      .slice(0, 5)
      .reverse() // Reverse to show highest ask first, lowest ask last (closest to spread)
    
    // Pad with empty levels if needed to always have 5 levels
    while (asks.length < 5) {
      asks.unshift({ price: 0, size: 0, level: asks.length + 1 }) // Add empty levels at top
    }
    
    // Calculate cumulative totals
    let cumulativeTotal = 0
    return asks.map((ask, index) => {
      if (ask.price > 0 && ask.size > 0) {
        cumulativeTotal += ask.size * ask.price
      }
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
    
    // Pad with empty levels if needed to always have 5 levels
    while (bids.length < 5) {
      bids.push({ price: 0, size: 0, level: bids.length + 1 }) // Add empty levels at bottom
    }
    
    // Calculate cumulative totals
    let cumulativeTotal = 0
    return bids.map((bid, index) => {
      if (bid.price > 0 && bid.size > 0) {
        cumulativeTotal += bid.size * bid.price
      }
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

  const pricePrecision = getPricePrecision()

  return (
    <div className="w-full bg-gray-900 border border-gray-700 flex flex-col">
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

      <div className="overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-2 text-xs text-gray-400 px-3 py-2 border-b border-gray-700 bg-gray-800">
          <div className="text-left">Price</div>
          <div className="text-right">Lot</div>
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
                  {ask.size > 0 ? formatLots(ask.size) : '-'}
                </div>
              </div>
            )
          })}
        </div>

        {/* Spread Section */}
        <div className="bg-gray-800 border-t border-b border-gray-600 py-1">
          <div className="text-center text-white font-mono text-xs">
            {((currentOrderBook.best_ask - currentOrderBook.best_bid) * Math.pow(10, pricePrecision)).toFixed(0)} points
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
                  {bid.size > 0 ? formatLots(bid.size) : '-'}
                </div>
              </div>
            )
          })}
        </div>
      </div>

    </div>
  )
}

