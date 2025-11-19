import { activityService } from '@main/services/ActivityService'
import { ScheduleNextTask } from './schedule-next-task'
import { BrowserWindow, ipcMain } from 'electron'
import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'
import { powerWatcher } from '../os/Power'
import { IpcChannel } from '@shared/IpcChannel'
import { getLogger } from '@shared/logger/main'

const logger = getLogger('LatestActivityTask')

class LatestActivityTask extends ScheduleNextTask {
  private listenerCount = 0
  private isSuspended = false

  constructor() {
    super()
  }

  init() {
    this.registerIpcEvent()
    powerWatcher.registerResumeCallback(() => this.onResume())
    powerWatcher.registerSuspendCallback(() => this.onSuspend())
    powerWatcher.registerLockScreenCallback(() => this.onSuspend())
    powerWatcher.registerUnlockScreenCallback(() => this.onResume())
  }

  private onSuspend() {
    if (this.isSuspended) return
    logger.debug('LatestActivityTask: System suspended or screen locked. Pausing polling.')
    this.isSuspended = true
    this.stopScheduleNextTask() // Force stop polling
  }

  private onResume() {
    if (!this.isSuspended) return
    logger.debug('LatestActivityTask: System resumed or screen unlocked.')
    this.isSuspended = false
    // If there are listeners, restart the polling
    if (this.listenerCount > 0) {
      logger.debug('LatestActivityTask: Resuming polling due to active listeners.')
      this.scheduleNextTask(true, this.runTasks.bind(this))
    }
  }

  // Called by the frontend to start listening
  async startTask() {
    this.listenerCount++
    logger.debug(`LatestActivityTask: Listener added. Count: ${this.listenerCount}`)
    // Only start if it's the first listener AND not suspended
    if (this.listenerCount === 1 && !this.isSuspended) {
      logger.debug('LatestActivityTask: Starting polling.')
      await this.scheduleNextTask(true, this.runTasks.bind(this))
    }
  }

  // Called by the frontend to stop listening
  stopTask() {
    if (this.listenerCount > 0) {
      this.listenerCount--
    }
    logger.debug(`LatestActivityTask: Listener removed. Count: ${this.listenerCount}`)
    // Only stop if it's the last listener
    if (this.listenerCount === 0) {
      logger.debug('LatestActivityTask: Stopping polling.')
      this.stopScheduleNextTask()
    }
  }

  async runTasks() {
    try {
      logger.debug('LatestActivityTask: Running task to get latest activity.')
      const res = await activityService.getLatestActivity()
      this.broadcastLatestActivity(res)
      logger.debug('LatestActivityTask: Task finished, data broadcasted.')
      return res
    } catch (error) {
      logger.error('LatestActivityTask: Error running task:', error)
      // Even if it fails, we return something to not break the await chain
      return undefined
    }
  }

  broadcastLatestActivity(res: Activity | undefined) {
    BrowserWindow.getAllWindows().forEach((window) => {
      window.webContents.send(IpcServerPushChannel.Home_PushLatestActivity, res)
    })
  }

  registerIpcEvent() {
    ipcMain.handle(IpcChannel.Get_Home_LatestActivity, (_, status: 'running' | 'stopped') => {
      if (status === 'running') {
        return this.startTask()
      } else if (status === 'stopped') {
        return this.stopTask()
      }
    })
  }
}

export { LatestActivityTask }
