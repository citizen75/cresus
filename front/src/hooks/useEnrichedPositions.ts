import { useState, useEffect } from 'react'
import { getApiBaseUrl } from '@/services/api'

export function useEnrichedPositions(positions: any[], portfolioName?: string) {
  const [enrichedPositions, setEnrichedPositions] = useState<any[]>([])
  const [fundamentalData, setFundamentalData] = useState<Record<string, any>>({})
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    const enrich = async () => {
      if (!positions || positions.length === 0) return

      setIsLoading(true)
      try {
        const baseUrl = getApiBaseUrl()
        const data: Record<string, any> = {}

        // Fetch fundamental data for all tickers
        for (const pos of positions) {
          try {
            const response = await fetch(`${baseUrl}/api/v1/data/fundamental/${pos.ticker}`)
            if (response.ok) {
              const result = await response.json()
              data[pos.ticker] = result?.data?.quotation || {}
            }
          } catch (error) {
            console.error(`Failed to fetch fundamental data for ${pos.ticker}:`, error)
            data[pos.ticker] = {}
          }
        }

        setFundamentalData(data)

        // Enrich positions with fundamental data and daily changes
        const enriched = positions.map((pos: any) => {
          const fund = data[pos.ticker] || {}
          const currentPrice = pos.current_price || 0
          const previousClose = fund.previous_close || currentPrice
          const quantity = pos.quantity || 0
          const avgEntryPrice = pos.avg_entry_price || 0

          // Daily change per share (not unrealized P&L)
          const daily_change = currentPrice - previousClose
          const daily_change_pct = previousClose && previousClose !== 0 ? ((currentPrice - previousClose) / previousClose) * 100 : 0

          // Unrealized P&L (total position gain/loss)
          const position_gain = pos.position_gain !== undefined ? pos.position_gain : (currentPrice - avgEntryPrice) * quantity
          const position_gain_pct = avgEntryPrice && avgEntryPrice !== 0 ? ((currentPrice - avgEntryPrice) / avgEntryPrice) * 100 : 0

          return {
            ...pos,
            position_gain,
            position_gain_pct,
            daily_change,
            daily_change_pct,
            asset_type: fund.asset_type || 'Stock',
            sector: fund.sector || 'Unknown',
          }
        })

        setEnrichedPositions(enriched)
      } catch (error) {
        console.error('Failed to enrich positions:', error)
      } finally {
        setIsLoading(false)
      }
    }

    enrich()
  }, [positions])

  return { enrichedPositions, fundamentalData, isLoading }
}
