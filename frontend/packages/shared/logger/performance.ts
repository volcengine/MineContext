import { app } from 'electron'
import path from 'path'
import fs from 'fs'
import inspector from 'node:inspector'
import pidusage from 'pidusage'
import v8 from 'node:v8'
import { PerformanceObserver } from 'perf_hooks'
import { mainLog as log } from './main'
import { is } from '@electron-toolkit/utils'
const eventLoopStats = require('event-loop-stats')

interface IProcessStats {
  cpu: number
  memory: number
  pid: number
  elapsed: number
}

interface IEventLoopStats {
  min: number
  max: number
  avg: number
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
      log.warn(`[Profiler] 🚀 已启动 CPU 分析, 标签: ${label}`)
    } catch (err: any) {
      log.error(`[Profiler] ❌ 启动失败: ${err.message}`)
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
          log.error(`[Profiler] ❌ 停止失败: ${err.message}`)
          return resolve(null)
        }
        const filename = `${Date.now()}-${label}.cpuprofile`
        const filepath = path.join(this.outDir, filename)
        fs.writeFileSync(filepath, JSON.stringify(profile))
        log.warn(`[Profiler] ✅ CPU 分析文件已保存至: ${filepath}`)
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

  constructor() {
    const profilesPath = path.join(!app.isPackaged && is.dev ? 'backend' : app.getPath('userData'))
    this.profiler = new CPUProfiler(path.join(profilesPath, 'profiles'))
    this.setupPerformanceObserver()
  }

  private setupPerformanceObserver(): void {
    const obs = new PerformanceObserver((items) => {
      items.getEntries().forEach((entry) => {
        if (entry.duration > this.thresholds.longOperation) {
          log.warn(`[Slow Op] 🐌 慢操作检测: ${entry.name} 耗时 ${entry.duration.toFixed(2)}ms`)
        }
      })
    })
    obs.observe({ entryTypes: ['measure'] })
  }

  private async getProcessStats(): Promise<IProcessStats | null> {
    try {
      const stats = await pidusage(process.pid)
      return {
        cpu: parseFloat(stats.cpu.toFixed(2)),
        memory: stats.memory,
        pid: stats.pid,
        elapsed: stats.elapsed
      }
    } catch (error: any) {
      log.error('❌ pidusage 获取失败:', error.message)
      return null
    }
  }

  private getEventLoopStats(): IEventLoopStats {
    const stats = eventLoopStats.sense()
    return {
      min: stats.min,
      max: stats.max,
      avg: stats.num > 0 ? parseFloat((stats.sum / stats.num).toFixed(2)) : 0
    }
  }

  private getV8HeapStats(): IV8HeapStats {
    const heapStats = v8.getHeapStatistics()
    return {
      totalHeapSize: this.formatBytes(heapStats.total_heap_size),
      usedHeapSize: this.formatBytes(heapStats.used_heap_size),
      heapSizeLimit: this.formatBytes(heapStats.heap_size_limit),
      numberOfDetachedContexts: heapStats.number_of_detached_contexts
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

    // CPU 持续过高
    if (metrics.process.cpu > this.thresholds.cpu) {
      anomalies.push({
        type: 'HIGH_CPU',
        severity: 'WARNING',
        message: `CPU使用率持续过高: ${metrics.process.cpu}%`,
        suggestion: '检查是否有密集计算、无限循环或频繁的I/O操作'
      })
    }

    // CPU 瞬时飙升
    if (this.baseline.cpu > 0) {
      const cpuIncrease = metrics.process.cpu - this.baseline.cpu
      if (cpuIncrease > this.thresholds.cpuSpike) {
        const anomaly: IAnomaly = {
          type: 'CPU_SPIKE',
          severity: 'CRITICAL',
          message: `CPU 突然飙升: ${this.baseline.cpu}% → ${metrics.process.cpu}% (增加了 ${cpuIncrease.toFixed(2)}%)`,
          suggestion: '已自动触发CPU分析, 请检查profiles目录下的.cpuprofile文件'
        }
        anomalies.push(anomaly)

        if (!this.profiler.isProfiling) {
          this.profiler.start('cpu-spike-trigger')
          setTimeout(async () => {
            const profilePath = await this.profiler.stop('cpu-spike-trigger')
            if (profilePath) {
              log.warn(`[Profiler] 自动分析完成, 触发原因: ${anomaly.message}`)
            }
          }, 15000) // 分析 15 秒
        }
      }
    }

    // 内存过高
    if (metrics.process.memory > this.thresholds.memory) {
      anomalies.push({
        type: 'HIGH_MEMORY',
        severity: 'WARNING',
        message: `内存使用过高: ${this.formatBytes(metrics.process.memory)}`,
        suggestion: '检查是否存在内存泄漏、大对象缓存或未释放的资源'
      })
    }

    // 事件循环延迟
    if (metrics.eventLoop.avg > this.thresholds.eventLoopLag) {
      anomalies.push({
        type: 'EVENT_LOOP_LAG',
        severity: metrics.eventLoop.avg > 1000 ? 'CRITICAL' : 'WARNING',
        message: `事件循环延迟过高: ${metrics.eventLoop.avg}ms (max: ${metrics.eventLoop.max}ms)`,
        suggestion: '检查同步阻塞代码、大量计算或阻塞I/O'
      })
    }

    // 游离上下文 (潜在内存泄漏)
    if (metrics.v8.numberOfDetachedContexts > 5) {
      anomalies.push({
        type: 'DETACHED_CONTEXTS',
        severity: 'WARNING',
        message: `检测到 ${metrics.v8.numberOfDetachedContexts} 个游离上下文`,
        suggestion: '可能存在内存泄漏, 检查未清理的DOM引用或闭包'
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
      eventLoop: this.getEventLoopStats(),
      v8: this.getV8HeapStats()
    }

    const anomalies = this.detectAnomalies(metrics)

    this.logMetrics(metrics, anomalies)

    // 更新基准值
    this.baseline.cpu = metrics.process.cpu
    this.baseline.memory = metrics.process.memory
  }

  private logMetrics(metrics: IMetrics, anomalies: IAnomaly[]): void {
    log.info(
      `[Perf] CPU: ${metrics.process.cpu}% | Mem: ${this.formatBytes(metrics.process.memory)} | Lag: ${metrics.eventLoop.avg}ms | Detached Ctx: ${metrics.v8.numberOfDetachedContexts}`
    )

    if (anomalies.length > 0) {
      log.warn('--- ⚠️ 性能异常 ---')
      anomalies.forEach((a) => {
        const icon = a.severity === 'CRITICAL' ? '🔴' : '🟡'
        log.warn(`${icon} [${a.type}] ${a.message}`)
        log.warn(`  💡 ${a.suggestion}`)
      })
      log.warn('--------------------')
    }
  }

  public start(interval: number = 5000): void {
    log.info('🚀 终极性能监控系统已启动 (TypeScript Version)')
    log.info(`💾 日志与分析文件路径: ${app.getPath('userData')}`)
    this.monitoringInterval = setInterval(() => this.collectAndLogMetrics(), interval)
  }

  public stop(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval)
      this.monitoringInterval = null
    }
    log.info('⏹️ 性能监控已停止')
  }
}

const monitor = new PerformanceMonitor()

export { monitor }
