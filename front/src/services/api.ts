import axios, { AxiosInstance } from 'axios'

class CresusAPI {
  private client: AxiosInstance

  constructor(baseURL: string = import.meta.env.VITE_API_URL || 'http://localhost:8000') {
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

  async getPortfolioHistory(name: string) {
    return (await this.client.get(`/portfolios/${name}/history`)).data
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
  }) {
    return (await this.client.put(`/portfolios/${portfolioName}/transactions/${transactionId}`, data)).data
  }

  async deleteTransaction(portfolioName: string, transactionId: string) {
    return (await this.client.delete(`/portfolios/${portfolioName}/transactions/${transactionId}`)).data
  }
}

export const api = new CresusAPI()
