import { useState, useEffect, useRef } from 'react'
import { getApiBaseUrl } from '@/services/api'

// Global cache for fundamental data (shared across component instances)
const fundamentalCache = new Map<string, any>()
let lastCacheTime = 0
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

export function useEnrichedPositions(positions: any[], portfolioName?: string) {
  const [enrichedPositions, setEnrichedPositions] = useState<any[]>([])
  const [fundamentalData, setFundamentalData] = useState<Record<string, any>>({})
  const [isLoading, setIsLoading] = useState(false)
  const fetchingRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    const enrich = async () => {
      if (!positions || positions.length === 0) return

      // Only fetch if we haven't already fetched this exact position list recently
      const positionTickers = positions.map(p => p.ticker).sort().join(',')
      if (fetchingRef.current.has(positionTickers)) {
        return // Already fetching this combination
      }

      setIsLoading(true)
      fetchingRef.current.add(positionTickers)

      try {
        const baseUrl = getApiBaseUrl()
        const data: Record<string, any> = {}

        // Separate cached vs uncached tickers
        const tickersToFetch: string[] = []
        for (const pos of positions) {
          if (fundamentalCache.has(pos.ticker)) {
            data[pos.ticker] = fundamentalCache.get(pos.ticker)
          } else {
            tickersToFetch.push(pos.ticker)
          }
        }

        // Fetch missing tickers in parallel (not sequentially!)
        if (tickersToFetch.length > 0) {
          console.log(`📡 Fetching ${tickersToFetch.length} tickers in parallel (${positions.length - tickersToFetch.length} cached)`)
          const promises = tickersToFetch.map(ticker =>
            fetch(`${baseUrl}/api/v1/data/fundamental/${ticker}`)
              .then(response => response.ok ? response.json() : null)
              .then(result => {
                const fundData = result?.data?.quotation || {}
                data[ticker] = fundData
                fundamentalCache.set(ticker, fundData) // Cache it
              })
              .catch(error => {
                console.error(`Failed to fetch fundamental data for ${ticker}:`, error)
                data[ticker] = {}
              })
          )
          await Promise.all(promises)
          lastCacheTime = Date.now()
        } else {
          console.log(`⚡ All ${positions.length} tickers cached`)
        }

        setFundamentalData(data)

        // Enrich positions with fundamental data and daily changes
        const enriched = positions.map((pos: any) => {
          const fund = data[pos.ticker] || {}
          const currentPrice = pos.current_price || 0
          const previousClose = fund.previous_close || currentPrice

          const daily_change = currentPrice - previousClose
          const daily_change_pct = previousClose && previousClose !== 0 ? ((currentPrice - previousClose) / previousClose) * 100 : 0

          return {
            ...pos,
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
        fetchingRef.current.delete(positionTickers)
      }
    }

    enrich()
  }, [positions])

  return { enrichedPositions, fundamentalData, isLoading }
}
