import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '@/services/api'

interface PortfolioData {
  details: any
  metrics: any
  history: any
  allocation: any
  topHoldings: any
  currentPrices: any
}

interface PortfolioContextType {
  portfolioName: string
  data: PortfolioData
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
  refreshData: (keys: (keyof PortfolioData)[]) => Promise<void>
}

const PortfolioContext = createContext<PortfolioContextType | undefined>(undefined)

interface PortfolioProviderProps {
  children: ReactNode
  portfolioName: string
}

export function PortfolioProvider({ children, portfolioName }: PortfolioProviderProps) {
  const [data, setData] = useState<PortfolioData>({
    details: null,
    metrics: null,
    history: null,
    allocation: null,
    topHoldings: null,
    currentPrices: null,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadAllData = async (forceRecalculate = false) => {
    setIsLoading(true)
    setError(null)
    try {
      const [details, metrics, history, allocation, topHoldings, currentPrices] = await Promise.all([
        api.getPortfolioDetails(portfolioName),
        api.getPortfolioMetrics(portfolioName),
        api.getPortfolioHistory(portfolioName, forceRecalculate),
        api.getPortfolioAllocation(portfolioName),
        api.getTopHoldings(portfolioName, 10),
        api.getCurrentPrices(portfolioName),
      ])

      setData({
        details,
        metrics,
        history,
        allocation,
        topHoldings,
        currentPrices,
      })
      console.log('Portfolio data loaded:', { details, metrics, history, allocation, topHoldings, currentPrices })
    } catch (err: any) {
      setError(err.message || 'Failed to load portfolio data')
      console.error('Portfolio load error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (portfolioName) {
      loadAllData()
    }
  }, [portfolioName])

  const refetch = async () => {
    await loadAllData(true)  // Force recalculation on manual refresh
  }

  const refreshData = async (keys: (keyof PortfolioData)[], forceRecalculate = true) => {
    try {
      const updates: Partial<PortfolioData> = {}

      if (keys.includes('details')) {
        updates.details = await api.getPortfolioDetails(portfolioName)
      }
      if (keys.includes('metrics')) {
        updates.metrics = await api.getPortfolioMetrics(portfolioName)
      }
      if (keys.includes('history')) {
        updates.history = await api.getPortfolioHistory(portfolioName, forceRecalculate)
      }
      if (keys.includes('allocation')) {
        updates.allocation = await api.getPortfolioAllocation(portfolioName)
      }
      if (keys.includes('topHoldings')) {
        updates.topHoldings = await api.getTopHoldings(portfolioName, 10)
      }
      if (keys.includes('currentPrices')) {
        updates.currentPrices = await api.getCurrentPrices(portfolioName)
      }

      setData((prev) => ({ ...prev, ...updates }))
    } catch (err) {
      console.error('Failed to refresh portfolio data:', err)
    }
  }

  const value: PortfolioContextType = {
    portfolioName,
    data,
    isLoading,
    error,
    refetch,
    refreshData,
  }

  return <PortfolioContext.Provider value={value}>{children}</PortfolioContext.Provider>
}

export function usePortfolioContext() {
  const context = useContext(PortfolioContext)
  if (context === undefined) {
    throw new Error('usePortfolioContext must be used within a PortfolioProvider')
  }
  return context
}
