
import { getLogger } from '@shared/logger/main'
import { app, BrowserWindow } from 'electron'
import { AppUpdater as _AppUpdater, autoUpdater, UpdateCheckResult, CancellationToken, UpdateInfo } from 'electron-updater'
import { IpcChannel } from '@shared/IpcChannel'
// import { isDev } from '@main/constant'
// import path from 'path'
const logger = getLogger('AppUpdater')

export default class AppUpdater {
  autoUpdater: _AppUpdater = autoUpdater
  private updateCheckResult: UpdateCheckResult | null = null
  private cancellationToken: CancellationToken = new CancellationToken()
  constructor(mainWindow: BrowserWindow) {
    autoUpdater.logger = logger
    // for dev test
    autoUpdater.forceDevUpdateConfig = !app.isPackaged

    // if (isDev) {
    //     const devConfigPath = path.join(process.cwd(), 'dev-app-update.yml')
    //     autoUpdater.updateConfigPath = devConfigPath
    //   // updateConfig
    //   logger.info('use dev update config2',  autoUpdater.updateConfigPath)
    // }

    autoUpdater.autoDownload = false
    autoUpdater.autoInstallOnAppQuit = false

    autoUpdater.on('checking-for-update', () => {
        logger.info('Checking for update...')
      })
      autoUpdater.on('update-available', (info: UpdateInfo) => {
        logger.info('Update available', info)
        mainWindow.webContents.send(IpcChannel.UpdateAvailable, info)
      })
      autoUpdater.on('update-not-available', () => {
        logger.info('Update not available.')
        mainWindow.webContents.send(IpcChannel.UpdateNotAvailable)
      })
      autoUpdater.on('error', (err) => {
        logger.info('Update error.', err)
        mainWindow.webContents.send(IpcChannel.UpdateError, err)
      })
      autoUpdater.on('update-downloaded', (info: UpdateInfo) => {
        logger.info('update downloaded', info)
        mainWindow.webContents.send(IpcChannel.UpdateDownloaded, info)
      })
  }
  public async checkForUpdates() {
    try {
      this.updateCheckResult = await this.autoUpdater.checkForUpdates()
      if (this.updateCheckResult?.isUpdateAvailable && !this.autoUpdater.autoDownload) {
        // 如果 autoDownload 为 false，则需要再调用下面的函数触发下
        // do not use await, because it will block the return of this function
        logger.info('downloadUpdate manual by check for updates', this.cancellationToken)
        this.autoUpdater.downloadUpdate(this.cancellationToken)
      }
      logger.info(
        `update check result: ${this.updateCheckResult?.isUpdateAvailable}, channel: ${this.autoUpdater.channel}, currentVersion: ${this.autoUpdater.currentVersion}`
      )
      return {
        currentVersion: this.autoUpdater.currentVersion,
        updateInfo: this.updateCheckResult?.isUpdateAvailable ? this.updateCheckResult?.updateInfo : null
      }
    } catch (error) {
      logger.error('Failed to check for update:', error as Error)
      return {
        currentVersion: app.getVersion(),
        updateInfo: null
      }
    }
  }
  public downloadUpdate() {
    this.autoUpdater.downloadUpdate()
  }

  public quitAndInstall() {
    setImmediate(() => autoUpdater.quitAndInstall())
  }

  public cancelDownload() {
    this.cancellationToken.cancel()
    this.cancellationToken = new CancellationToken()
    if (this.autoUpdater.autoDownload) {
      this.updateCheckResult?.cancellationToken?.cancel()
    }
  }
}
