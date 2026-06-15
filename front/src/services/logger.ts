/**
 * Centralized logging service
 * Logs only in development mode, configurable per level
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

class Logger {
  private isDev = process.env.NODE_ENV === 'development'

  debug(message: string, data?: unknown) {
    if (this.isDev) {
      console.log(`[DEBUG] ${message}`, data)
    }
  }

  info(message: string, data?: unknown) {
    if (this.isDev) {
      console.log(`[INFO] ${message}`, data)
    }
  }

  warn(message: string, data?: unknown) {
    console.warn(`[WARN] ${message}`, data)
  }

  error(message: string, error?: Error | unknown) {
    console.error(`[ERROR] ${message}`, error)
  }
}

export const logger = new Logger()
