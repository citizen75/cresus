import { useState, useCallback } from 'react'

/**
 * Centralized hook for loading historical data across all chart widgets.
 * Encapsulates data fetching logic to keep components clean and reusable.
 */
export function useHistoricalDataLoader() {
  const [historicalData, setHistoricalData] = useState<{ [ticker: string]: any[] }>({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(
    async (
      tickers: string[],
      fetchFn: (ticker: string, days: number) => Promise<any>,
      days: number = 1825
    ) => {
      if (!tickers.length || !fetchFn) return

      try {
        setIsLoading(true)
        setError(null)
        const loaded: { [ticker: string]: any[] } = {}

        for (const ticker of tickers) {
          try {
            const response = await fetchFn(ticker, days)
            if (response && response.data) {
              loaded[ticker] = response.data
            }
          } catch (err) {
            console.error(`Failed to load data for ${ticker}:`, err)
          }
        }

        setHistoricalData(loaded)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load data'
        setError(message)
        console.error('Error loading historical data:', err)
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  return {
    historicalData,
    isLoading,
    error,
    loadData,
    setHistoricalData,
  }
}
