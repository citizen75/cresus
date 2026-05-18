export function getCurrencySymbol(currency: string = 'USD'): string {
  const symbols: Record<string, string> = {
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'JPY': '¥',
    'CHF': 'CHF',
    'CAD': 'C$',
    'AUD': 'A$',
  }
  return symbols[currency.toUpperCase()] || currency
}

export function formatCurrency(value: number, currency: string = 'USD'): string {
  const symbol = getCurrencySymbol(currency)
  const locale = currency === 'USD' ? 'en-US' : currency === 'EUR' ? 'de-DE' : 'en-US'
  const formatted = value.toLocaleString(locale, { maximumFractionDigits: 2 })
  return `${symbol}${formatted}`
}
