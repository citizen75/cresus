import axios, { AxiosInstance } from 'axios'

export function getApiBaseUrl(): string {
  // Priority: env var > construct from hostname with API port
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  
  // Use same hostname as frontend, but API port (8000)
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    // For localhost, use port 8000; for other hosts (192.168.x.x, etc), use port 8000
    return `http://${hostname}:8000`
  }
  
  return 'http://localhost:8000'
}

class CresusAPI {
  private client: AxiosInstance

  constructor(baseURL: string = getApiBaseUrl()) {
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

  async getHistoricalData(ticker: string, days?: number) {
    const params = days ? { days } : {}
    return (await this.client.get(`/data/history/${ticker}`, { params })).data
  }

  async getFundamental(ticker: string) {
    return (await this.client.get(`/data/fundamental/${ticker}`)).data
  }
}

export const api = new CresusAPI()
