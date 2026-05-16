import axios, { AxiosInstance } from 'axios'

let cachedApiUrl: string | null = null

export async function fetchApiConfig(): Promise<string> {
  // Return cached URL if available
  if (cachedApiUrl) {
    return cachedApiUrl
  }

  // Priority 1: Environment variable
  if (import.meta.env.VITE_API_URL) {
    cachedApiUrl = import.meta.env.VITE_API_URL
    api.updateBaseURL(cachedApiUrl)
    return cachedApiUrl
  }

  // Priority 2: Fetch config from backend
  try {
    // Try to fetch config from standard location (localhost:8000)
    const configResponse = await axios.get('http://localhost:8000/api/v1/config', {
      timeout: 2000
    })
    const { api: apiConfig } = configResponse.data
    const host = apiConfig.host || 'localhost'
    const port = apiConfig.port || 8000
    cachedApiUrl = `http://${host}:${port}`
    api.updateBaseURL(cachedApiUrl)
    return cachedApiUrl
  } catch (err) {
    // Config fetch failed, fall back to hostname-based URL
  }

  // Priority 3: Use same hostname as frontend with default port
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    cachedApiUrl = `http://${hostname}:8000`
    api.updateBaseURL(cachedApiUrl)
    return cachedApiUrl
  }

  // Fallback
  cachedApiUrl = 'http://localhost:8000'
  api.updateBaseURL(cachedApiUrl)
  return cachedApiUrl
}

export function getApiBaseUrl(): string {
  // Return cached URL or default
  return cachedApiUrl || 'http://localhost:8000'
}

class CresusAPI {
  private client: AxiosInstance

  constructor() {
    // Use default initially, will be updated after config is fetched
    const baseURL = getApiBaseUrl()
    this.client = axios.create({
      baseURL: `${baseURL}/api/v1`,
      timeout: 30000,
    })
  }

  updateBaseURL(baseURL: string) {
    this.client = axios.create({
      baseURL: `${baseURL}/api/v1`,
      timeout: 30000,
    })
  }

  async getHealth() {
    return (await this.client.get('/health')).data
  }

  async listPortfolios() {
    return (await this.client.get('/portfolios')).data
  }

  async listStrategies() {
    return (await this.client.get('/strategies')).data
  }

  async listUniverses() {
    return (await this.client.get('/data/universes')).data
  }

  async getStrategy(name: string) {
    return (await this.client.get(`/strategies/${name}`)).data
  }

  async updateStrategy(name: string, data: any) {
    return (await this.client.put(`/strategies/${name}`, data)).data
  }

  async duplicateStrategy(name: string, newName?: string) {
    const params = newName ? { new_name: newName } : {}
    return (await this.client.post(`/strategies/${name}/duplicate`, {}, { params })).data
  }

  async deleteStrategy(name: string) {
    return (await this.client.delete(`/strategies/${name}`)).data
  }

  async getPortfolioDetails(name: string) {
    return (await this.client.get(`/portfolios/${name}`)).data
  }

  async getPortfolioValue(name: string) {
    return (await this.client.get(`/portfolios/${name}/value`)).data
  }

  async getPortfolioMetrics(name: string) {
    return (await this.client.get(`/portfolios/${name}/metrics`)).data
  }

  async getPortfolioHistory(name: string, recalculate: boolean = false) {
    return (await this.client.get(`/portfolios/${name}/history`, {
      params: { recalculate }
    })).data
  }

  async getPortfolioAllocation(name: string) {
    return (await this.client.get(`/portfolios/${name}/allocation`)).data
  }

  async getTopHoldings(name: string, limit: number = 10) {
    return (await this.client.get(`/portfolios/${name}/holdings?limit=${limit}`)).data
  }

  async createPortfolio(data: {
    name: string
    portfolio_type: string
    currency: string
    description: string
    initial_capital: number
  }) {
    return (await this.client.post('/portfolios', data)).data
  }

  async updatePortfolio(name: string, data: {
    portfolio_type?: string
    currency?: string
    description?: string
    initial_capital?: number
  }) {
    return (await this.client.put(`/portfolios/${name}`, data)).data
  }

  async deletePortfolio(name: string) {
    return (await this.client.delete(`/portfolios/${name}`)).data
  }

  async recordTransaction(portfolioName: string, data: {
    operation: string
    ticker: string
    quantity: number
    price: number
    fees?: number
    notes?: string
    created_at?: string
  }) {
    return (await this.client.post(`/portfolios/${portfolioName}/transactions`, data)).data
  }

  async getCurrentPrices(name: string) {
    return (await this.client.get(`/portfolios/${name}/current-prices`)).data
  }

  async getPortfolioWatchlist(name: string, limit: number = 50) {
    return (await this.client.get(`/portfolios/${name}/watchlist`, { params: { limit } })).data
  }

  async getTransactions(portfolioName: string, ticker?: string) {
    const params = ticker ? `?ticker=${ticker}` : ''
    return (await this.client.get(`/portfolios/${portfolioName}/transactions${params}`)).data
  }

  async updateTransaction(portfolioName: string, transactionId: string, data: {
    quantity?: number
    price?: number
    fees?: number
    notes?: string
    created_at?: string
  }) {
    return (await this.client.put(`/portfolios/${portfolioName}/transactions/${transactionId}`, data)).data
  }

  async deleteTransaction(portfolioName: string, transactionId: string) {
    return (await this.client.delete(`/portfolios/${portfolioName}/transactions/${transactionId}`)).data
  }

  async listBacktests(strategy?: string) {
    const params = strategy ? { strategy } : {}
    return (await this.client.get('/backtests', { params })).data
  }

  async getBacktest(strategy: string, id: string) {
    return (await this.client.get(`/backtests/${strategy}/${id}`)).data
  }

  async runBacktest(data: {
    strategy: string
    start_date?: string
    end_date?: string
    portfolio_name?: string
  }) {
    return (await this.client.post('/backtests', data)).data
  }

  async compareBacktests(items: string[]) {
    const itemsStr = items.join(',')
    return (await this.client.get('/backtests/compare', { params: { items: itemsStr } })).data
  }

  async getBacktestMetrics(strategy: string, id: string) {
    return (await this.client.get(`/backtests/${strategy}/${id}/metrics`)).data
  }

  async getBacktestDistribution(strategy: string, id: string) {
    return (await this.client.get(`/backtests/${strategy}/${id}/distribution`)).data
  }

  async deleteBacktest(strategy: string, id: string) {
    return (await this.client.delete(`/backtests/${strategy}/${id}`)).data
  }

  async getHistoricalData(ticker: string, days?: number, options?: { indicator?: string }) {
    const params: any = days ? { days } : {}
    if (options?.indicator) {
      params.indicator = options.indicator
    }
    return (await this.client.get(`/data/history/${ticker}`, { params })).data
  }

  async getFundamental(ticker: string) {
    return (await this.client.get(`/data/fundamental/${ticker}`)).data
  }

  async getBacktestWatchlist(strategy: string, backtest_id?: string) {
    // Load from portfolio directory (live mode) or backtest directory (legacy)
    const endpoint = backtest_id
      ? `/backtests/${strategy}/${backtest_id}/watchlist`
      : `/backtests/strategy/${strategy}/watchlist`
    return (await this.client.get(endpoint)).data
  }

  async regenerateBacktestWatchlist(strategy: string) {
    // Run strategy in live mode
    return (await this.client.post(`/backtests`, { strategy })).data
  }
}

export const api = new CresusAPI()
