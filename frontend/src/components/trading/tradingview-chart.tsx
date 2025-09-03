'use client'

import { useEffect, useRef, useState } from 'react'
import { useMarketStore } from '@/store/market'
import { tradingViewDatafeed } from '@/lib/tradingview-datafeed'

declare global {
  interface Window {
    TradingView: any
  }
}

interface TradingViewChartProps {
  symbol?: string
}

export function TradingViewChart({ symbol }: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const widgetRef = useRef<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const { selectedSymbol } = useMarketStore()
  const currentSymbol = symbol || selectedSymbol

  useEffect(() => {
    const loadTradingViewScript = () => {
      return new Promise<void>((resolve, reject) => {
        if (window.TradingView) {
          resolve()
          return
        }

        const script = document.createElement('script')
        script.src = '/charting_library/charting_library/charting_library.standalone.js'
        script.async = true
        script.onload = () => resolve()
        script.onerror = () => reject(new Error('Failed to load TradingView script'))
        document.head.appendChild(script)
      })
    }

    const initializeChart = async () => {
      try {
        setIsLoading(true)
        setError(null)

        await loadTradingViewScript()

        if (!chartContainerRef.current || !window.TradingView) {
          throw new Error('TradingView library not loaded or container not found')
        }

        if (widgetRef.current) {
          widgetRef.current.remove()
        }

        const widget = new window.TradingView.widget({
          container: chartContainerRef.current,
          width: '100%',
          height: '100%',
          symbol: currentSymbol,
          interval: '60',
          datafeed: tradingViewDatafeed,
          library_path: '/charting_library/charting_library/',
          locale: 'en',
          disabled_features: [
            'use_localstorage_for_settings',
            'volume_force_overlay',
            'create_volume_indicator_by_default',
            'header_symbol_search',
            'header_resolutions',
            'header_chart_type',
            'header_settings',
            'header_indicators',
            'header_compare',
            'header_undo_redo',
            'header_screenshot',
            'header_fullscreen_button'
          ],
          enabled_features: [
            'study_templates'
          ],
          charts_storage_url: '',
          charts_storage_api_version: '1.1',
          client_id: 'fix-trading-platform',
          user_id: 'public_user_id',
          fullscreen: false,
          autosize: true,
          studies_overrides: {},
          theme: 'dark',
          custom_css_url: '/charting_library/themed.css',
          loading_screen: {
            backgroundColor: '#111827',
            foregroundColor: '#3b82f6'
          },
          overrides: {
            'paneProperties.background': '#111827',
            'paneProperties.vertGridProperties.color': '#374151',
            'paneProperties.horzGridProperties.color': '#374151',
            'symbolWatermarkProperties.transparency': 90,
            'scalesProperties.textColor': '#9ca3af',
            'scalesProperties.backgroundColor': '#1f2937'
          },
          studies_overrides: {
            'volume.volume.color.0': '#ef4444',
            'volume.volume.color.1': '#22c55e',
            'volume.volume.transparency': 65
          }
        })

        widgetRef.current = widget

        widget.onChartReady(() => {
          setIsLoading(false)
          console.log('TradingView chart ready for symbol:', currentSymbol)
        })

      } catch (err) {
        console.error('Error initializing TradingView chart:', err)
        setError(err instanceof Error ? err.message : 'Failed to load chart')
        setIsLoading(false)
      }
    }

    if (currentSymbol) {
      initializeChart()
    }

    return () => {
      if (widgetRef.current) {
        try {
          widgetRef.current.remove()
        } catch (err) {
          console.error('Error removing TradingView widget:', err)
        }
      }
    }
  }, [currentSymbol])

  if (error) {
    return (
      <div className="flex-1 bg-gray-900 rounded-lg border border-gray-700 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 mb-2">Chart Error</div>
          <div className="text-gray-400 text-sm">{error}</div>
          <div className="text-xs text-gray-500 mt-2">
            Make sure TradingView library is properly installed
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 bg-gray-900 rounded-lg border border-gray-700 relative">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900 rounded-lg z-10">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
            <div className="text-gray-400">Loading chart...</div>
            <div className="text-xs text-gray-500 mt-1">{currentSymbol}</div>
          </div>
        </div>
      )}
      <div 
        ref={chartContainerRef} 
        className="w-full h-full rounded-lg"
        style={{ minHeight: '400px' }}
      />
    </div>
  )
}
