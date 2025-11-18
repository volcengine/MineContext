import { getLogger } from '@shared/logger/main'

const logger = getLogger('ScheduleNextTask')
class ScheduleNextTask {
  private scheduleNextTaskTimer: NodeJS.Timeout | null = null
  private POLLING_INTERVAL_MS = 15 * 1000

  updateInterval(time: number = 15 * 1000) {
    this.POLLING_INTERVAL_MS = time
  }

  public scheduleNextTask<T extends (...params: any[]) => Promise<any>>(immediate = false, runTasks: T) {
    if (this.scheduleNextTaskTimer) {
      clearTimeout(this.scheduleNextTaskTimer)
    }

    const run = async () => {
      const startTime = Date.now()

      try {
        await runTasks()
      } catch (error) {
        // The error should be logged inside runTasks, but we catch here
        // to ensure the polling loop doesn't die.
        logger.error('Polling task failed, but the loop will continue:', error)
      }

      const executionTime = Date.now() - startTime

      // Dynamically calculate the delay for the next run to correct for drift.
      const nextDelay = Math.max(0, this.POLLING_INTERVAL_MS - executionTime)

      this.scheduleNextTaskTimer = setTimeout(run, nextDelay)
    }

    if (immediate) {
      run()
    } else {
      // For the very first run, use the full interval if not immediate.
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

export { ScheduleNextTask }
