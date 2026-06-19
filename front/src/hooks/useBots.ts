import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'

export function useBots(state?: 'active' | 'inactive') {
  return useQuery({
    queryKey: ['bots', state],
    queryFn: () => api.listBots(state),
    staleTime: 30_000,
  })
}

export function useBotsSummary() {
  return useQuery({
    queryKey: ['bots-summary'],
    queryFn: () => api.getBotsSummary(),
    staleTime: 30_000,
  })
}

export function useBot(name: string) {
  return useQuery({
    queryKey: ['bot', name],
    queryFn: () => api.getBot(name),
    staleTime: 30_000,
    enabled: !!name,
  })
}

export function useBotWatchlist(name: string, limit?: number) {
  return useQuery({
    queryKey: ['bot-watchlist', name, limit],
    queryFn: () => api.getBotWatchlist(name, limit),
    staleTime: 30_000,
    enabled: !!name,
  })
}

export function useBotOrders(name: string) {
  return useQuery({
    queryKey: ['bot-orders', name],
    queryFn: () => api.getBotOrders(name),
    staleTime: 30_000,
    enabled: !!name,
  })
}
