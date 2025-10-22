// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { app } from 'electron'
import path from 'path'
import fs from 'fs'
import inspector from 'inspector'
import pidusage from 'pidusage'
import v8 from 'v8'
import { PerformanceObserver, monitorEventLoopDelay, IntervalHistogram } from 'perf_hooks'
import { is } from '@electron-toolkit/utils'
import Logger from 'electron-log/main'
import dayjs from 'dayjs'

const log = Logger.create({ logId: 'performance' })
log.transports.console.level = false
log.transports.file.level = 'debug'
log.transports.file.maxSize = 10 * 1024 * 1024
log.transports.file.format = '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] [{processType}] {text}'
log.transports.file.resolvePathFn = () => {
  // ✨ Dynamically generate log paths, split by "process-date"
  const day = dayjs().format('YYYY-MM-DD')
  const name = `${process.type}-${day}.log`
  // Differentiate log storage locations for development and production environments
  const logDir = path.join(
    !app.isPackaged && is.dev ? 'backend' : app.getPath('userData'),
    'frontend-logs', // Store uniformly in the logs subdirectory
    'performance'
  )
  return path.join(logDir, name)
}
interface IProcessStats {
  cpu: number
  memory: number
  pid: number
  elapsed: number
}
interface IEventLoopStats {
  min: number
  max: number
  mean: number
  p50: number
  p99: number
}
interface IV8HeapStats {
  usedHeapSize: string
  totalHeapSize: string
  heapSizeLimit: string
  numberOfDetachedContexts: number
}
interface IMetrics {
  timestamp: string
  process: IProcessStats
  eventLoop: IEventLoopStats
  v8: IV8HeapStats
}
interface IAnomaly {
  type: 'HIGH_CPU' | 'CPU_SPIKE' | 'HIGH_MEMORY' | 'EVENT_LOOP_LAG' | 'DETACHED_CONTEXTS'
  severity: 'WARNING' | 'CRITICAL'
  message: string
  suggestion: string
}

class CPUProfiler {
  private session: inspector.Session | null = null
  public isProfiling: boolean = false
  private outDir: string

  constructor(outputDirectory: string) {
    this.outDir = outputDirectory
    if (!fs.existsSync(this.outDir)) {
      fs.mkdirSync(this.outDir, { recursive: true })
    }
  }

  public start(label: string = 'profile'): void {
    if (this.isProfiling) return
    this.session = new inspector.Session()
    try {
      this.session.connect()
      this.session.post('Profiler.enable')
      this.session.post('Profiler.start')
      this.isProfiling = true
      log.warn(`[Profiler] 🚀 Started CPU Profile, label: ${label}`)
    } catch (err: any) {
      log.error(`[Profiler] ❌ Failed to start: ${err.message}`)
    }
  }

  public async stop(label: string = 'profile'): Promise<string | null> {
    if (!this.isProfiling || !this.session) return null
    return new Promise((resolve) => {
      this.session?.post('Profiler.stop', (err, { profile }) => {
        this.isProfiling = false
        try {
          this.session?.disconnect()
        } catch {}
        this.session = null
        if (err) {
          log.error(`[Profiler] ❌ Failed to stop: ${err.message}`)
          return resolve(null)
        }
        const filename = `${Date.now()}-${label}.cpuprofile`
        const filepath = path.join(this.outDir, filename)
        fs.writeFileSync(filepath, JSON.stringify(profile))
        log.warn(`[Profiler] ✅ CPU Profile saved to: ${filepath}`)
        resolve(filepath)
      })
    })
  }
}

class PerformanceMonitor {
  private profiler: CPUProfiler
  private thresholds = {
    cpu: 70,
    memory: 500 * 1024 * 1024,
    cpuSpike: 30,
    eventLoopLag: 100,
    longOperation: 1000
  }
  private baseline = { cpu: 0, memory: 0 }
  private monitoringInterval: NodeJS.Timeout | null = null
  private eventLoopHistogram: IntervalHistogram | null = null

  constructor() {
    this.profiler = new CPUProfiler(
      path.join(!app.isPackaged && is.dev ? 'backend' : app.getPath('userData'), 'profiles')
    )
    this.setupPerformanceObserver()
  }

  private setupPerformanceObserver(): void {
    const obs = new PerformanceObserver((items) => {
      items.getEntries().forEach((entry) => {
        if (entry.duration > this.thresholds.longOperation) {
          log.warn(`[Slow Op] 🐌 Slow operation detected: "${entry.name}" took ${entry.duration.toFixed(2)}ms`)
        }
      })
    })
    obs.observe({ entryTypes: ['measure'] })
  }

  private async getProcessStats(): Promise<IProcessStats | null> {
    try {
      const stats = await pidusage(process.pid)
      return { cpu: parseFloat(stats.cpu.toFixed(2)), memory: stats.memory, pid: stats.pid, elapsed: stats.elapsed }
    } catch (error: any) {
      log.error('❌ pidusage failed:', error.message)
      return null
    }
  }

  private getEventLoopStats(): IEventLoopStats | null {
    if (!this.eventLoopHistogram) return null
    const toMs = (ns: number) => parseFloat((ns / 1_000_000).toFixed(2))
    return {
      min: toMs(this.eventLoopHistogram.min),
      max: toMs(this.eventLoopHistogram.max),
      mean: toMs(this.eventLoopHistogram.mean),
      p50: toMs(this.eventLoopHistogram.percentile(50)),
      p99: toMs(this.eventLoopHistogram.percentile(99))
    }
  }

  private getV8HeapStats(): IV8HeapStats {
    const h = v8.getHeapStatistics()
    return {
      totalHeapSize: this.formatBytes(h.total_heap_size),
      usedHeapSize: this.formatBytes(h.used_heap_size),
      heapSizeLimit: this.formatBytes(h.heap_size_limit),
      numberOfDetachedContexts: h.number_of_detached_contexts
    }
  }

  private formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
  }

  private detectAnomalies(metrics: IMetrics): IAnomaly[] {
    const anomalies: IAnomaly[] = []
    if (metrics.process.cpu > this.thresholds.cpu) {
      anomalies.push({
        type: 'HIGH_CPU',
        severity: 'WARNING',
        message: `High CPU usage: ${metrics.process.cpu}%`,
        suggestion: 'Check for intensive computations, loops, or frequent I/O.'
      })
    }
    if (this.baseline.cpu > 0) {
      const cpuIncrease = metrics.process.cpu - this.baseline.cpu
      if (cpuIncrease > this.thresholds.cpuSpike) {
        const anomaly: IAnomaly = {
          type: 'CPU_SPIKE',
          severity: 'CRITICAL',
          message: `CPU Spike detected: ${this.baseline.cpu}% → ${metrics.process.cpu}% (+${cpuIncrease.toFixed(2)}%)`,
          suggestion: 'Auto-triggered CPU profile. Check the .cpuprofile file in the profiles directory.'
        }
        anomalies.push(anomaly)
        if (!this.profiler.isProfiling) {
          this.profiler.start('cpu-spike-trigger')
          setTimeout(() => {
            this.profiler.stop('cpu-spike-trigger').then((profilePath) => {
              if (profilePath) log.warn(`[Profiler] Profile for spike completed, triggered by: ${anomaly.message}`)
            })
          }, 15000)
        }
      }
    }
    if (metrics.process.memory > this.thresholds.memory) {
      anomalies.push({
        type: 'HIGH_MEMORY',
        severity: 'WARNING',
        message: `High memory usage: ${this.formatBytes(metrics.process.memory)}`,
        suggestion: 'Check for memory leaks, large object caching, or unreleased resources.'
      })
    }
    if (metrics.eventLoop && metrics.eventLoop.mean > this.thresholds.eventLoopLag) {
      anomalies.push({
        type: 'EVENT_LOOP_LAG',
        severity: metrics.eventLoop.mean > 1000 ? 'CRITICAL' : 'WARNING',
        message: `High Event Loop Lag: mean=${metrics.eventLoop.mean}ms, max=${metrics.eventLoop.max}ms, p99=${metrics.eventLoop.p99}ms`,
        suggestion: 'Check for synchronous blocking code or intensive computations.'
      })
    }
    if (metrics.v8.numberOfDetachedContexts > 5) {
      anomalies.push({
        type: 'DETACHED_CONTEXTS',
        severity: 'WARNING',
        message: `Detected ${metrics.v8.numberOfDetachedContexts} detached contexts`,
        suggestion: 'Potential memory leak. Check for un-cleaned DOM references or closures.'
      })
    }
    return anomalies
  }

  private async collectAndLogMetrics(): Promise<void> {
    const processStats = await this.getProcessStats()
    if (!processStats) return
    const metrics: IMetrics = {
      timestamp: new Date().toISOString(),
      process: processStats,
      eventLoop: this.getEventLoopStats()!,
      v8: this.getV8HeapStats()
    }
    const anomalies = this.detectAnomalies(metrics)
    this.logMetrics(metrics, anomalies)
    this.baseline.cpu = metrics.process.cpu
    this.baseline.memory = metrics.process.memory
  }

  private logMetrics(metrics: IMetrics, anomalies: IAnomaly[]): void {
    const lag = metrics.eventLoop ? `Lag(p99): ${metrics.eventLoop.p99}ms` : 'Lag: N/A'
    log.info(
      `[Perf] CPU: ${metrics.process.cpu}% | Mem: ${this.formatBytes(metrics.process.memory)} | ${lag} | Detached Ctx: ${metrics.v8.numberOfDetachedContexts}`
    )
    if (anomalies.length > 0) {
      log.warn('--- ⚠️ Performance Anomaly Detected ---')
      anomalies.forEach((a) => {
        const icon = a.severity === 'CRITICAL' ? '🔴' : '🟡'
        log.warn(`${icon} [${a.type}] ${a.message}`)
        log.warn(`  💡 Suggestion: ${a.suggestion}`)
      })
      log.warn('--------------------------------------')
    }
  }

  public start(interval: number = 5000): void {
    log.info('🚀 Ultimate Performance Monitor Started (TypeScript/Native ELD Version)')
    this.eventLoopHistogram = monitorEventLoopDelay({ resolution: 20 })
    this.eventLoopHistogram.enable()
    log.info(`💾 Logs & profiles will be saved to: ${app.getPath('userData')}`)
    this.monitoringInterval = setInterval(() => this.collectAndLogMetrics(), interval)
  }

  public stop(): void {
    if (this.monitoringInterval) clearInterval(this.monitoringInterval)
    this.eventLoopHistogram?.disable()
    log.info('⏹️ Performance Monitor Stopped')
  }
}

const monitor = new PerformanceMonitor()

// ipcMain.on('log-renderer-performance', (event: IpcMainEvent, entry: any) => {
//   const winId = BrowserWindow.fromWebContents(event.sender)?.id ?? 'N/A'
//   const msg = `[Window-${winId}] [${entry.type}] "${entry.name}" took ${entry.duration}ms`
//   if (entry.type === 'Long Task') {
//     log.warn(msg, entry.details ? { details: entry.details } : {})
//   } else {
//     log.info(msg)
//   }
// })
export { monitor }
