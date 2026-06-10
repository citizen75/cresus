import axios, { AxiosInstance } from 'axios'

export function getApiBaseUrl(): string {
  // Use values injected at build time from .cresus/.env via import.meta.env
  const host = import.meta.env.VITE_API_HOST || 'localhost'
  const port = import.meta.env.VITE_API_PORT || '8000'
  return `http://${host}:${port}`
}

class CresusAPI {
  private client: AxiosInstance
  private longTimeoutClient: AxiosInstance

  constructor() {
    // Use default initially, will be updated after config is fetched
    const baseURL = getApiBaseUrl()
    this.client = axios.create({
      baseURL: `${baseURL}/api/v1`,
      timeout: 30000,
    })
    this.longTimeoutClient = axios.create({
      baseURL: `${baseURL}/api/v1`,
      timeout: 150000, // 2.5 minutes for long-running operations
    })
  }

  updateBaseURL(baseURL: string) {
    this.client = axios.create({
      baseURL: `${baseURL}/api/v1`,
      timeout: 30000,
    })
    this.longTimeoutClient = axios.create({
      baseURL: `${baseURL}/api/v1`,
      timeout: 150000, // 2.5 minutes
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

  async getPortfolioMetadata(name: string) {
    return (await this.client.get(`/portfolios/${name}/metadata`)).data
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

  async getPortfolioHistory(name: string, fetch: boolean = false) {
    return (await this.client.get(`/portfolios/${name}/history`, {
      params: { fetch }
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

  // Scheduler/Cron management
  async listCronJobs() {
    return (await this.client.get('/scheduler/jobs')).data
  }

  async getCronJob(name: string) {
    return (await this.client.get(`/scheduler/jobs/${name}`)).data
  }

  async createCronJob(data: {
    name: string
    schedule: string
    target: string
    job_type?: string
    description?: string
    params?: Record<string, any>
    enabled?: boolean
  }) {
    const params = new URLSearchParams()
    params.append('name', data.name)
    params.append('schedule', data.schedule)
    params.append('target', data.target)
    if (data.job_type) params.append('job_type', data.job_type)
    if (data.description) params.append('description', data.description)
    if (data.params) params.append('params', JSON.stringify(data.params))
    if (data.enabled !== undefined) params.append('enabled', String(data.enabled))

    return (await this.client.post('/scheduler/jobs', null, { params })).data
  }

  async updateCronJob(name: string, data: {
    schedule?: string
    target?: string
    job_type?: string
    description?: string
    params?: Record<string, any>
    enabled?: boolean
  }) {
    const params = new URLSearchParams()
    if (data.schedule) params.append('schedule', data.schedule)
    if (data.target) params.append('target', data.target)
    if (data.job_type) params.append('job_type', data.job_type)
    if (data.description) params.append('description', data.description)
    if (data.params) params.append('params', JSON.stringify(data.params))
    if (data.enabled !== undefined) params.append('enabled', String(data.enabled))

    return (await this.client.put(`/scheduler/jobs/${name}`, null, { params })).data
  }

  async enableCronJob(name: string) {
    return (await this.client.post(`/scheduler/jobs/${name}/enable`)).data
  }

  async disableCronJob(name: string) {
    return (await this.client.post(`/scheduler/jobs/${name}/disable`)).data
  }

  async runCronJob(name: string) {
    return (await this.longTimeoutClient.post(`/scheduler/jobs/${name}/run`)).data
  }

  async duplicateCronJob(name: string, newName: string) {
    const params = new URLSearchParams()
    params.append('new_name', newName)
    return (await this.client.post(`/scheduler/jobs/${name}/duplicate`, null, { params })).data
  }

  async deleteCronJob(name: string) {
    return (await this.client.delete(`/scheduler/jobs/${name}`)).data
  }

  // Screener management
  async listScreeners() {
    return (await this.client.get('/screener/screeners')).data
  }

  async getScreener(name: string) {
    return (await this.client.get(`/screener/screeners/${name}`)).data
  }

  async createScreener(data: {
    name: string
    source?: string
    tickers?: string
    indicators?: string
    formula?: string
    description?: string
  }) {
    const params = new URLSearchParams()
    params.append('name', data.name)
    if (data.source) params.append('source', data.source)
    if (data.tickers) params.append('tickers', data.tickers)
    if (data.indicators) params.append('indicators', data.indicators)
    if (data.formula) params.append('formula', data.formula)
    if (data.description) params.append('description', data.description)

    return (await this.client.post('/screener/screeners', null, { params })).data
  }

  async updateScreener(name: string, data: {
    source?: string
    tickers?: string
    indicators?: string
    formula?: string
    description?: string
  }) {
    const params = new URLSearchParams()
    if (data.source) params.append('source', data.source)
    if (data.tickers) params.append('tickers', data.tickers)
    if (data.indicators) params.append('indicators', data.indicators)
    if (data.formula) params.append('formula', data.formula)
    if (data.description) params.append('description', data.description)

    return (await this.client.put(`/screener/screeners/${name}`, null, { params })).data
  }

  async deleteScreener(name: string) {
    return (await this.client.delete(`/screener/screeners/${name}`)).data
  }

  async runScreener(name: string) {
    return (await this.longTimeoutClient.post(`/screener/screeners/${name}/run`)).data
  }

  async listScreenerResults(name: string) {
    return (await this.client.get(`/screener/screeners/${name}/results`)).data
  }

  async getScreenerResult(name: string, resultId: string) {
    return (await this.client.get(`/screener/screeners/${name}/results/${resultId}`)).data
  }

  async deleteScreenerResult(name: string, resultId: string) {
    return (await this.client.delete(`/screener/screeners/${name}/results/${resultId}`)).data
  }

  async clearScreenerResults(name: string) {
    return (await this.client.post(`/screener/screeners/${name}/results/clear`)).data
  }

  async screenerBuilder(formula: string, source?: string, tickers?: string[]) {
    const params: any = { formula }
    if (source) params.source = source
    if (tickers) params.tickers = JSON.stringify(tickers)
    return (await this.longTimeoutClient.post('/screener/builder', null, { params })).data
  }

  // Alert management
  async listAlerts() {
    return (await this.client.get('/alerts')).data
  }

  async getAlert(name: string) {
    return (await this.client.get(`/alerts/${name}`)).data
  }

  async createAlert(data: {
    name: string
    source: string
    source_value?: string
    formula: string
    notify?: string
    description?: string
    tags?: string[]
  }) {
    const params = new URLSearchParams()
    params.append('name', data.name)
    params.append('source', data.source)
    if (data.source_value) params.append('source_value', data.source_value)
    params.append('formula', data.formula)
    if (data.notify) params.append('notify', data.notify)
    if (data.description) params.append('description', data.description)
    if (data.tags) params.append('tags', data.tags.join(','))

    return (await this.client.post('/alerts', null, { params })).data
  }

  async updateAlert(name: string, data: {
    formula?: string
    enabled?: boolean
    description?: string
    tags?: string[]
    notify?: string
  }) {
    const params = new URLSearchParams()
    if (data.formula) params.append('formula', data.formula)
    if (data.enabled !== undefined) params.append('enabled', String(data.enabled))
    if (data.description) params.append('description', data.description)
    if (data.tags) params.append('tags', data.tags.join(','))
    if (data.notify) params.append('notify', data.notify)

    return (await this.client.put(`/alerts/${name}`, null, { params })).data
  }

  async deleteAlert(name: string) {
    return (await this.client.delete(`/alerts/${name}`)).data
  }

  async runAlert(name: string) {
    return (await this.longTimeoutClient.post(`/alerts/${name}/run`)).data
  }

  async getAlertLogs(alertName: string, lines: number = 200) {
    return (await this.client.get(`/alerts/${alertName}/logs?lines=${lines}`)).data
  }

  async getAlertResults(alertName: string, limit: number = 10) {
    return (await this.client.get(`/alerts/${alertName}/results?limit=${limit}`)).data
  }

  async deleteAlertResult(alertName: string, resultId: string) {
    return (await this.client.delete(`/alerts/${alertName}/results/${resultId}`)).data
  }

  async getConversationHistory(
    portfolioName: string,
    limit?: number,
    source?: string
  ) {
    const params: any = {}
    if (limit) params.limit = limit
    if (source) params.source = source
    return (await this.client.get(`/conversations/${portfolioName}`, { params })).data
  }

  async sendConversationMessage(data: {
    text: string
    widget?: string
    data?: any
  }) {
    // Send to global conversation (portfolio_name = "global")
    // Format: { source, content, widget, data }
    const message = {
      source: 'alert',
      content: data.text,
      widget: data.widget,
      data: data.data,
    }
    return (await this.client.post('/conversations/global/message', message)).data
  }

  async listWatchlists() {
    return (await this.client.get('/watchlists')).data
  }

  async getWatchlist(watchlistName: string, limit?: number) {
    const response = (await this.client.get(`/watchlists/${watchlistName}`, { params: { limit } })).data
    // Transform watchlist records to results format
    return {
      ...response,
      results: response.watchlist || [],
      tickers: response.watchlist?.map((item: any) => item.ticker) || [],
    }
  }

  async addToWatchlist(watchlistName: string, ticker: string) {
    return (await this.client.post(`/watchlists/${watchlistName}/add`, { ticker })).data
  }

  async removeFromWatchlist(watchlistName: string, ticker: string) {
    return (await this.client.delete(`/watchlists/${watchlistName}/${ticker}`)).data
  }

  async getWatchlistTickers(watchlistName: string) {
    return (await this.client.get(`/watchlists/${watchlistName}/tickers`)).data
  }
}

export const api = new CresusAPI()
