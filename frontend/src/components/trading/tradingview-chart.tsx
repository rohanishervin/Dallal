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
  const [priceType, setPriceType] = useState<'B' | 'A'>('B')
  
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

        // Update datafeed with current price type
        tradingViewDatafeed.setPriceType(priceType)

        const widget = new window.TradingView.widget({
          container: chartContainerRef.current,
          width: '100%',
          height: '100%',
          symbol: currentSymbol,
          interval: '15',
          datafeed: tradingViewDatafeed,
          library_path: '/charting_library/charting_library/',
          locale: 'en',
          timezone: 'Etc/UTC',
          disabled_features: [
            'use_localstorage_for_settings',
            'volume_force_overlay',
            'create_volume_indicator_by_default',
            'header_symbol_search',
            'header_screenshot',
            'header_fullscreen_button'
          ],
          enabled_features: [
            'study_templates',
            'header_resolutions',
            'header_chart_type',
            'header_settings',
            'header_indicators',
            'header_compare',
            'header_undo_redo',
            'timeframes_toolbar',
            'edit_buttons_in_legend',
            'context_menus',
            'control_bar',
            'timeframes_toolbar'
          ],
          charts_storage_url: '',
          charts_storage_api_version: '1.1',
          client_id: 'fix-trading-platform',
          user_id: 'public_user_id',
          fullscreen: false,
          autosize: true,
          studies_overrides: {},
          theme: 'dark',
          loading_screen: {
            backgroundColor: '#000000',
            foregroundColor: '#ffffff'
          },
          overrides: {
            // Main chart background - pure black theme
            'paneProperties.background': '#000000',
            'paneProperties.backgroundGradientStartColor': '#000000',
            'paneProperties.backgroundGradientEndColor': '#000000',
            'paneProperties.backgroundType': 'solid',
            
            // Additional background overrides
            'mainSeriesProperties.priceLineColor': '#6b7280',
            'mainSeriesProperties.priceLineWidth': 1,
            'mainSeriesProperties.priceLineStyle': 2,
            
            // Chart container background
            'chartProperties.background': '#000000',
            'chartProperties.backgroundType': 'solid',
            'chartProperties.backgroundGradientStartColor': '#000000',
            'chartProperties.backgroundGradientEndColor': '#000000',
            
            // Grid lines - darker gray
            'paneProperties.vertGridProperties.color': '#1f2937',
            'paneProperties.horzGridProperties.color': '#1f2937',
            'paneProperties.vertGridProperties.style': 0,
            'paneProperties.horzGridProperties.style': 0,
            
            // Symbol watermark
            'symbolWatermarkProperties.transparency': 90,
            'symbolWatermarkProperties.color': '#4b5563',
            
            // Price scales
            'scalesProperties.textColor': '#d1d5db',
            'scalesProperties.backgroundColor': '#000000',
            'scalesProperties.lineColor': '#1f2937',
            
            // Candlestick colors
            'mainSeriesProperties.candleStyle.upColor': '#22c55e',
            'mainSeriesProperties.candleStyle.downColor': '#ef4444',
            'mainSeriesProperties.candleStyle.borderUpColor': '#22c55e',
            'mainSeriesProperties.candleStyle.borderDownColor': '#ef4444',
            'mainSeriesProperties.candleStyle.wickUpColor': '#22c55e',
            'mainSeriesProperties.candleStyle.wickDownColor': '#ef4444',
            
            // Hollow candlesticks
            'mainSeriesProperties.hollowCandleStyle.upColor': '#22c55e',
            'mainSeriesProperties.hollowCandleStyle.downColor': '#ef4444',
            'mainSeriesProperties.hollowCandleStyle.borderUpColor': '#22c55e',
            'mainSeriesProperties.hollowCandleStyle.borderDownColor': '#ef4444',
            'mainSeriesProperties.hollowCandleStyle.wickUpColor': '#22c55e',
            'mainSeriesProperties.hollowCandleStyle.wickDownColor': '#ef4444',
            
            // Bar chart colors
            'mainSeriesProperties.barStyle.upColor': '#22c55e',
            'mainSeriesProperties.barStyle.downColor': '#ef4444',
            
            // Line chart colors
            'mainSeriesProperties.lineStyle.color': '#9ca3af',
            'mainSeriesProperties.lineStyle.linewidth': 2,
            
            // Area chart colors
            'mainSeriesProperties.areaStyle.color1': '#6b7280',
            'mainSeriesProperties.areaStyle.color2': '#4b5563',
            'mainSeriesProperties.areaStyle.linecolor': '#9ca3af',
            
            // Baseline colors
            'mainSeriesProperties.baselineStyle.baselineColor': '#6b7280',
            'mainSeriesProperties.baselineStyle.topFillColor1': 'rgba(34, 197, 94, 0.3)',
            'mainSeriesProperties.baselineStyle.topFillColor2': 'rgba(34, 197, 94, 0.1)',
            'mainSeriesProperties.baselineStyle.bottomFillColor1': 'rgba(239, 68, 68, 0.3)',
            'mainSeriesProperties.baselineStyle.bottomFillColor2': 'rgba(239, 68, 68, 0.1)',
            
            // High-Low colors
            'mainSeriesProperties.hiloStyle.color': '#9ca3af',
            'mainSeriesProperties.hiloStyle.showBorders': true,
            'mainSeriesProperties.hiloStyle.borderColor': '#6b7280',
            
            // Cross hair
            'crossHairProperties.color': '#6b7280',
            'crossHairProperties.width': 1,
            'crossHairProperties.style': 2,
            
            // Legend
            'legendProperties.showLegend': true,
            'legendProperties.showStudyArguments': false,
            'legendProperties.showStudyTitles': true,
            'legendProperties.showStudyValues': true,
            'legendProperties.showSeriesTitle': true,
            'legendProperties.showBarChange': true,
            
            // Session breaks
            'mainSeriesProperties.sessionBreaks.color': '#374151',
            'mainSeriesProperties.sessionBreaks.style': 2,
            'mainSeriesProperties.sessionBreaks.width': 1
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
          
          // Force dark background on chart container
          setTimeout(() => {
            const chartFrames = chartContainerRef.current?.querySelectorAll('iframe')
            chartFrames?.forEach(frame => {
              try {
                if (frame.contentDocument) {
                  const body = frame.contentDocument.body
                  if (body) {
                    body.style.backgroundColor = '#000000 !important'
                    body.style.background = '#000000 !important'
                  }
                  
                  const chartContainers = frame.contentDocument.querySelectorAll('[class*="chart"], [class*="pane"], [class*="background"]')
                  chartContainers.forEach(container => {
                    if (container instanceof HTMLElement) {
                      container.style.backgroundColor = '#000000 !important'
                      container.style.background = '#000000 !important'
                    }
                  })
                }
              } catch (e) {
                // Cross-origin restrictions, ignore
              }
            })
          }, 1000)
          
          // Add custom Bid/Ask toggle button to toolbar
          widget.headerReady().then(() => {
            const button = widget.createButton()
            button.setAttribute('title', 'Toggle between Bid and Ask prices')
            button.classList.add('apply-common-tooltip')
            
            // Style the button to match TradingView's native buttons
            button.style.cssText = `
              background: rgba(42, 46, 57, 1);
              border: 1px solid rgba(55, 65, 81, 1);
              border-radius: 6px;
              padding: 6px 10px;
              margin: 0 2px;
              cursor: pointer;
              transition: all 0.15s ease;
              display: flex;
              align-items: center;
              gap: 6px;
              height: 28px;
              box-sizing: border-box;
            `
            
            // Chart icon SVG
            const chartIcon = `
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink: 0;">
                <path d="M13.75 12.0837L10.25 8.58366L8.91667 10.5837L6.25 7.91699" stroke="currentcolor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
                <path d="M12.0835 12.0837H13.7502V10.417" stroke="currentcolor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
                <path d="M7.49984 18.3337H12.4998C16.6665 18.3337 18.3332 16.667 18.3332 12.5003V7.50033C18.3332 3.33366 16.6665 1.66699 12.4998 1.66699H7.49984C3.33317 1.66699 1.6665 3.33366 1.6665 7.50033V12.5003C1.6665 16.667 3.33317 18.3337 7.49984 18.3337Z" stroke="currentcolor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
              </svg>
            `
            
            const updateButton = (type: 'B' | 'A') => {
              const color = type === 'B' ? '#22c55e' : '#ef4444'
              const text = type === 'B' ? 'Bid' : 'Ask'
              
              button.innerHTML = `
                <div style="color: ${color}; display: flex; align-items: center; gap: 6px;">
                  ${chartIcon}
                  <span style="font-size: 12px; font-weight: 500; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">${text}</span>
                </div>
              `
              
              button.setAttribute('title', `Currently showing ${text} prices - Click to switch to ${type === 'B' ? 'Ask' : 'Bid'}`)
              
              // Update button state
              button.style.background = type === 'B' 
                ? 'rgba(34, 197, 94, 0.15)' 
                : 'rgba(239, 68, 68, 0.15)'
              button.style.borderColor = type === 'B' 
                ? 'rgba(34, 197, 94, 0.4)' 
                : 'rgba(239, 68, 68, 0.4)'
            }
            
            updateButton(priceType)
            
            // Button hover effects
            button.addEventListener('mouseenter', () => {
              button.style.background = priceType === 'B' 
                ? 'rgba(34, 197, 94, 0.25)' 
                : 'rgba(239, 68, 68, 0.25)'
              button.style.borderColor = priceType === 'B' 
                ? 'rgba(34, 197, 94, 0.6)' 
                : 'rgba(239, 68, 68, 0.6)'
              button.style.transform = 'translateY(-1px)'
              button.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.15)'
            })
            
            button.addEventListener('mouseleave', () => {
              button.style.background = priceType === 'B' 
                ? 'rgba(34, 197, 94, 0.15)' 
                : 'rgba(239, 68, 68, 0.15)'
              button.style.borderColor = priceType === 'B' 
                ? 'rgba(34, 197, 94, 0.4)' 
                : 'rgba(239, 68, 68, 0.4)'
              button.style.transform = 'translateY(0)'
              button.style.boxShadow = 'none'
            })
            
            // Simple toggle click handler
            button.addEventListener('click', () => {
              const newPriceType = priceType === 'B' ? 'A' : 'B'
              setPriceType(newPriceType)
              updateButton(newPriceType)
            })
          })
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
  }, [currentSymbol, priceType])

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
    <div className="w-full h-full bg-gray-900 rounded-lg border border-gray-700 relative overflow-hidden">
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
        className="w-full h-full"
        style={{ 
          minHeight: '100%',
          backgroundColor: '#111827'
        }}
      />
    </div>
  )
}
