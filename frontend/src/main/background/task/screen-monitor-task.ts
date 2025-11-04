import { CaptureSource } from '@interface/common/source'
import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'
import { BrowserWindow, ipcMain } from 'electron'
import { get, pick, uniqBy } from 'lodash'
import screenshotService from '../../services/ScreenshotService'
import { AutoRefreshCache } from './cache-value'
import { getLogger } from '@shared/logger/main'
import PQueue from 'p-queue'
import axios from 'axios'
import { getBackendPort } from '@main/backend'
import dayjs, { Dayjs } from 'dayjs'
import { IpcChannel } from '@shared/IpcChannel'
import { powerWatcher } from '../os/Power'
import isBetween from 'dayjs/plugin/isBetween'
import customParseFormat from 'dayjs/plugin/customParseFormat'
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter'
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore'
dayjs.extend(isBetween)
dayjs.extend(customParseFormat)
dayjs.extend(isSameOrAfter)
dayjs.extend(isSameOrBefore)
const queue = new PQueue({ concurrency: 3 })

const logger = getLogger('ScreenMonitorTask')
class ScheduleNextTask {
  private scheduleNextTaskTimer: NodeJS.Timeout | null = null
  private POLLING_INTERVAL_MS = 15 * 1000
  updateInterval(time: number = 15 * 1000) {
    this.POLLING_INTERVAL_MS = time
  }
  public scheduleNextTask<T extends (...params: any[]) => any>(immediate = false, runTasks: T) {
    // 清除上一个定时器（如果有的话），防止重复执行
    if (this.scheduleNextTaskTimer) {
      clearTimeout(this.scheduleNextTaskTimer)
    }

    const run = async () => {
      await runTasks()
      this.scheduleNextTaskTimer = setTimeout(run, this.POLLING_INTERVAL_MS)
    }

    if (immediate) {
      run()
    } else {
      // 正常调度
      this.scheduleNextTaskTimer = setTimeout(run, this.POLLING_INTERVAL_MS)
    }
  }
  public stopScheduleNextTask() {
    if (this.scheduleNextTaskTimer) {
      clearTimeout(this.scheduleNextTaskTimer)
      this.scheduleNextTaskTimer = null
    }
  }
}

class ScreenMonitorTask extends ScheduleNextTask {
  static globalStatus: 'running' | 'stopped' = 'stopped'
  private status: 'running' | 'stopped' = 'stopped'
  private appInfo: CaptureSource[] = []
  private configCache: AutoRefreshCache<CaptureSource[]> | null = null
  private modelConfig: Record<string, unknown> = {}
  constructor() {
    super()
  }
  public async init() {
    this.listenToScreenMonitorEvents()
    this.configCache = new AutoRefreshCache<CaptureSource[]>({
      fetchFn: async () => {
        return await this.getVisibleSourcesUseCache()
      },
      interval: 3 * 1000,
      immediate: true
    })
    logger.info('ScreenMonitorTask initialized')
  }
  private listenToScreenMonitorEvents() {
    ipcMain.handle(IpcChannel.Task_Update_Current_Record_App, (_, appInfo: CaptureSource[]) => {
      logger.info(
        'ScreenMonitorTask updateCurrentRecordApp -->',
        appInfo.map((v) => pick(v, ['name', 'type']))
      )
      this.appInfo = uniqBy([...this.appInfo, ...appInfo], 'id')
      this.configCache?.triggerUpdate(true)
    })
    ipcMain.handle(IpcChannel.Task_Update_Model_Config, (_, config: Record<string, unknown>) => {
      this.modelConfig = config
      this.updateInterval(config.interval as number)
    })
    ipcMain.handle(IpcChannel.Task_Start, () => {
      logger.info('render notify ScreenMonitorTask start')
      ScreenMonitorTask.globalStatus = 'running'
      this.startTask()
    })
    ipcMain.handle(IpcChannel.Task_Stop, () => {
      logger.info('render notify ScreenMonitorTask stop')
      ScreenMonitorTask.globalStatus = 'stopped'
      this.stopTask()
    })
    ipcMain.handle(IpcChannel.Task_Check_Can_Record, () => {
      return {
        canRecord: this.checkCanRecord(),
        status: this.status
      }
    })
    powerWatcher.registerResumeCallback(() => {
      logger.info('ScreenMonitorTask resume')
      if (ScreenMonitorTask.globalStatus === 'running') {
        this.startTask()
      }
    })
    powerWatcher.registerSuspendCallback(() => {
      logger.info('ScreenMonitorTask suspend')
      this.stopTask()
    })
    powerWatcher.registerLockScreenCallback(() => {
      logger.info('ScreenMonitorTask lock-screen', ScreenMonitorTask.globalStatus)
      this.stopTask()
    })
    powerWatcher.registerUnlockScreenCallback(() => {
      logger.info('ScreenMonitorTask unlock-screen', ScreenMonitorTask.globalStatus)
      if (ScreenMonitorTask.globalStatus === 'running') {
        this.startTask()
      }
    })
  }
  private async startTask() {
    if (this.status === 'running') {
      return
    }

    logger.info('ScreenMonitorTask startTask', this.configCache)
    this.configCache?.start()
    this.scheduleNextTask(true, this.startScreenMonitor.bind(this))
    this.status = 'running'
    this.broadcastStatus()
  }
  private stopTask() {
    if (this.status === 'stopped') {
      return
    }
    logger.info('ScreenMonitorTask stopTask')
    this.configCache?.stop()
    this.stopScheduleNextTask()
    this.status = 'stopped'
    this.broadcastStatus()
    // clear queue
    queue.clear()
  }

  private async getVisibleSourcesUseCache() {
    try {
      const res = await screenshotService.getVisibleSources()
      logger.info('getVisibleSourcesUseCache', res)
      if (res.sources) {
        return res.sources
      } else {
        return []
      }
    } catch (error) {
      logger.error('getVisibleSourcesUseCache error', error)
      return []
    }
  }
  private async handleScreenshotTask(source: CaptureSource, createTime: Dayjs) {
    const res = await screenshotService.takeScreenshot(source.id, createTime)

    if (res.success) {
      logger.info(`Screenshot taken successfully for source ${source.id}`)
      const url = get(res, 'screenshotInfo.url') || ''
      if (url) {
        await this.uploadImage(url, source.type, createTime)
      }
    } else {
      throw new Error(res.error || 'Unknown error')
    }
  }
  private async startScreenMonitor() {
    try {
      const visibleSources = this.configCache?.get()
      logger.info(
        'visibleSources',
        visibleSources?.map((item) => pick(item, ['name', 'type', 'isVisible']))
      )
      const ids = visibleSources?.map((item) => (item.isVisible ? item.id : '')).filter(Boolean) || []
      if (!visibleSources || ids.length === 0) {
        logger.warn('screen monitor visibleSources is empty')
        return
      }
      if (!this.checkCanRecord()) {
        logger.warn('screen monitor not in record time')
        return
      }

      const sources = this.appInfo.filter((source) => ids.includes(source.id))
      logger.info(
        'sources',
        sources.map((v) => pick(v, ['name', 'type']))
      )
      const createTime = dayjs()
      sources.forEach((source) => {
        queue.add(() => this.handleScreenshotTask(source, createTime))
      })
      logger.info(`Queue has ${queue.size} tasks. Waiting for idle...`)
      // await queue.onIdle()
      // logger.info('All screenshot tasks have completed.')
    } catch (error) {
      this.stopTask()
      logger.error('startScreenMonitor error', error)
    }
  }
  private broadcastStatus() {
    BrowserWindow.getAllWindows().forEach((window) => {
      window.webContents.send(IpcServerPushChannel.PushScreenMonitorStatus, this.status)
    })
  }

  public unregister() {
    queue.clear()
    this.configCache?.destroy()
    this.status = 'stopped'
    this.stopScheduleNextTask()

    ipcMain.removeHandler(IpcChannel.Task_Update_Model_Config)
    ipcMain.removeHandler(IpcChannel.Task_Start)
    ipcMain.removeHandler(IpcChannel.Task_Stop)
    ipcMain.removeHandler(IpcChannel.Task_Update_Current_Record_App)
  }

  private async uploadImage(url: string, type: CaptureSource['type'], createTime: Dayjs) {
    try {
      const data = {
        path: url,
        window: type === 'screen' ? 'screen' : '',
        create_time: createTime.format('YYYY-MM-DD HH:mm:ss'),
        app: type === 'window' ? 'window' : ''
      }
      const res = await axios.post(`http://127.0.0.1:${getBackendPort()}/api/add_screenshot`, data)
      if (res.status === 200) {
        logger.info('Screenshot uploaded successfully')
      } else {
        logger.error('Screenshot upload failed', res.status)
      }
    } catch (error) {
      logger.error('Failed to upload screenshot:', error)
    }
  }

  private checkCanRecord = () => {
    const { enableRecordingHours, applyToDays, recordingHours } = this.modelConfig

    if (!enableRecordingHours) {
      return true
    }

    const now = dayjs()

    if (applyToDays === 'weekday') {
      const currentDay = now.day()
      if (currentDay === 0 || currentDay === 6) {
        return false
      }
    }

    if (recordingHours && Array.isArray(recordingHours) && recordingHours.length === 2) {
      const [startTimeStr, endTimeStr] = recordingHours as [string, string] // e.g., ["09:00", "18:00"]

      const start = dayjs(startTimeStr, 'HH:mm')
      const end = dayjs(endTimeStr, 'HH:mm')

      if (!start.isValid() || !end.isValid()) {
        logger.warn(`invalid record time format: ${startTimeStr}-${endTimeStr}。skip check`)
        return true
      }

      if (start.isAfter(end)) {
        return now.isSameOrAfter(start) || now.isSameOrBefore(end)
      } else {
        return now.isBetween(start, end, null, '[]')
      }
    }
    return true
  }
}
export { ScreenMonitorTask }
