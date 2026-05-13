import { useQuery } from '@tanstack/react-query'
import { QueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export function usePortfolios() {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: () => api.listPortfolios(),
    staleTime: 30_000,
  })
}

export function usePortfolioDetails(name: string) {
  return useQuery({
    queryKey: ['portfolio-details', name],
    queryFn: () => api.getPortfolioDetails(name),
    staleTime: 60_000,
    enabled: !!name,
  })
}

export function usePortfolioMetrics(name: string) {
  return useQuery({
    queryKey: ['portfolio-metrics', name],
    queryFn: () => api.getPortfolioMetrics(name),
    staleTime: 5 * 60_000,
    enabled: !!name,
  })
}

export function usePortfolioHistory(name: string) {
  return useQuery({
    queryKey: ['portfolio-history', name],
    queryFn: () => api.getPortfolioHistory(name, true), // Always recalculate for fresh data
    staleTime: 60_000, // 1 minute
    enabled: !!name,
  })
}

export function usePortfolioAllocation(name: string) {
  return useQuery({
    queryKey: ['portfolio-allocation', name],
    queryFn: () => api.getPortfolioAllocation(name),
    staleTime: 60_000,
    enabled: !!name,
  })
}

export function useTopHoldings(name: string, limit: number = 10) {
  return useQuery({
    queryKey: ['top-holdings', name, limit],
    queryFn: () => api.getTopHoldings(name, limit),
    staleTime: 60_000,
    enabled: !!name,
  })
}

export function useCurrentPrices(name: string) {
  return useQuery({
    queryKey: ['current-prices', name],
    queryFn: () => api.getCurrentPrices(name),
    staleTime: 30_000, // 30 seconds - prices update frequently
    enabled: !!name,
    refetchInterval: 60_000, // Refetch every minute
  })
}

export function useBacktestRuns(strategy?: string) {
  return useQuery({
    queryKey: ['backtest-runs', strategy],
    queryFn: () => api.listBacktests(strategy),
    staleTime: 30_000,
  })
}

export function useBacktestRun(strategy: string, id: string) {
  return useQuery({
    queryKey: ['backtest-run', strategy, id],
    queryFn: () => api.getBacktest(strategy, id),
    staleTime: 60_000,
    enabled: !!strategy && !!id,
  })
}

export function useBacktestMetrics(strategy: string, id: string) {
  return useQuery({
    queryKey: ['backtest-metrics', strategy, id],
    queryFn: () => api.getBacktestMetrics(strategy, id),
    staleTime: 60_000,
    enabled: !!strategy && !!id,
  })
}

export function useBacktestDistribution(strategy: string, id: string) {
  return useQuery({
    queryKey: ['backtest-distribution', strategy, id],
    queryFn: () => api.getBacktestDistribution(strategy, id),
    staleTime: 60_000,
    enabled: !!strategy && !!id,
  })
}
