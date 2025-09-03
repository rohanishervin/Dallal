'use client'

import { useEffect } from 'react'
import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import { PriceChart } from '@/components/trading/price-chart'
import { MarketWatch } from '@/components/trading/market-watch'
import { OrderBook } from '@/components/trading/order-book'
import { TradePanel } from '@/components/trading/trade-panel'
import { LoginModal } from '@/components/auth/login-modal'
import { useAuthStore } from '@/store/auth'
import { useMarketStore } from '@/store/market'

export default function TradingDashboard() {
  const { isAuthenticated, checkSession } = useAuthStore()
  const { loadInstruments } = useMarketStore()

  useEffect(() => {
    checkSession()
  }, [checkSession])

  useEffect(() => {
    if (isAuthenticated) {
      loadInstruments()
    }
  }, [isAuthenticated, loadInstruments])

  return (
    <div className="h-screen bg-gray-950 flex">
      <LoginModal isOpen={!isAuthenticated} />
      
      <div className={`flex-1 flex ${!isAuthenticated ? 'blur-sm' : ''}`}>
        <Sidebar />
        
        <div className="flex-1 flex flex-col">
          <Header />
          
          <div className="flex-1 p-6 flex gap-6 overflow-hidden">
            <div className="flex-1 flex flex-col gap-6">
              <PriceChart />
              
              <div className="h-48 bg-gray-900 rounded-lg border border-gray-700 p-4">
                <h3 className="text-white font-medium mb-4">Positions & Orders</h3>
                <div className="text-gray-400 text-sm">
                  No active positions or orders
                </div>
              </div>
            </div>
            
            <div className="flex flex-col gap-6">
              <MarketWatch />
              <OrderBook />
              <TradePanel />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}