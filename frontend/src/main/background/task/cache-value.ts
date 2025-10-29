import dayjs from 'dayjs'
import _ from 'lodash'

export interface CacheOptions<T> {
  fetchFn: () => Promise<T>
  interval?: number
  immediate?: boolean
  minInterval?: number
  initialValue?: T
}

export class AutoRefreshCache<T> {
  private value?: T
  private lastUpdated?: dayjs.Dayjs
  private timer?: ReturnType<typeof setInterval>
  private readonly interval: number
  private readonly fetchFn: () => Promise<T>
  private readonly immediate: boolean
  private readonly minInterval: number
  private isRunning = false

  constructor(options: CacheOptions<T>) {
    this.fetchFn = options.fetchFn
    this.interval = options.interval ?? 60 // 默认 60s
    this.immediate = options.immediate ?? true
    this.minInterval = options.minInterval ?? Math.min(this.interval, 3) // 默认最小间隔：min( interval, 3s )
    this.value = options.initialValue
  }

  get(): T | undefined {
    return this.value
  }

  getLastUpdated(): string | undefined {
    return this.lastUpdated?.format('YYYY-MM-DD HH:mm:ss')
  }

  isExpired(): boolean {
    if (!this.lastUpdated) return true
    return dayjs().diff(this.lastUpdated, 'second') >= this.interval
  }

  private async doUpdate(): Promise<void> {
    if (this.isRunning) {
      return
    }
    this.isRunning = true
    try {
      const data = await this.fetchFn()
      this.value = data
      this.lastUpdated = dayjs()
    } catch (err) {
      console.error('[AutoRefreshCache] update failed:', err)
    } finally {
      this.isRunning = false
    }
  }

  async triggerUpdate(force = false): Promise<void> {
    if (!force && this.lastUpdated) {
      const diffSec = dayjs().diff(this.lastUpdated, 'second')
      if (diffSec < this.minInterval) {
        return
      }
    }
    await this.doUpdate()
  }

  start(): void {
    this.stop()

    if (this.immediate) {
      this.triggerUpdate(true).catch((err) => {
        console.error('[AutoRefreshCache] immediate update error:', err)
      })
    }

    this.timer = setInterval(() => {
      this.triggerUpdate(false).catch((err) => {
        console.error('[AutoRefreshCache] scheduled update error:', err)
      })
    }, this.interval * 1000)
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = undefined
    }
  }

  destroy(): void {
    this.stop()
    this.value = undefined
    this.lastUpdated = undefined
    this.isRunning = false
  }
}
