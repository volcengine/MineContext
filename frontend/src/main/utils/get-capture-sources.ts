// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { app, desktopCapturer, DesktopCapturerSource, systemPreferences } from 'electron'
import screenshot from 'screenshot-desktop'
import { exec, spawn } from 'node:child_process'
import { promisify } from 'node:util'
import { getLogger } from '@shared/logger/main'
import { FinalWindowInfo, getAllWindows } from './mac-window-manager'
import { NativeCaptureHelper } from './native-capture-helper'
import path from 'node:path'
const logger = getLogger('ScreenshotService')

/**
 * @interface CaptureSource
 * @description The final, unified structure for a capture source sent to the frontend.
 */
export interface CaptureSource {
  id: string
  name: string
  type: 'screen' | 'window'
  thumbnail: string | null
  appIcon: string | null
  isVisible: boolean
  // Optional properties for windows added from the native module
  isVirtual?: boolean
  appName?: string
  windowTitle?: string
  windowId?: number
}

class CaptureSourcesTools {
  private nativeCaptureHelper: NativeCaptureHelper | null = null
  constructor() {
    if (process.platform === 'darwin') {
      try {
        this.nativeCaptureHelper = new NativeCaptureHelper()
        this.nativeCaptureHelper.initialize()
        logger.info('✅ Native capture helper initialized')
      } catch (error: any) {
        logger.warn(`⚠️ Native capture helper failed to initialize: ${error.message}`)
        this.nativeCaptureHelper = null // Clear the helper so fallback logic works
      }
    }
  }

  async getCaptureSourcesTools() {
    try {
      const sources = await desktopCapturer.getSources({
        types: ['window', 'screen'],
        thumbnailSize: { width: 256, height: 144 },
        fetchWindowIcons: true
      })

      const formattedSources: CaptureSource[] = sources.map((source) => {
        let displayName = source.name

        return {
          id: source.id,
          name: displayName,
          type: source.display_id ? 'screen' : 'window',
          thumbnail: source.thumbnail.toDataURL(),
          appIcon: source.appIcon ? source.appIcon.toDataURL() : null,
          isVisible: true // desktopCapturer only returns visible windows
        }
      })

      if (process.platform === 'darwin') {
        try {
          let allWindows: FinalWindowInfo[] = []

          logger.info('Using macWindowManager for cross-space window detection')
          allWindows = await getAllWindows()

          const windowsByApp = new Map()

          const realAppNames = new Map()

          for (const macWindow of allWindows) {
            const macTitle = macWindow.windowTitle.toLowerCase()
            const macApp = macWindow.appName

            const matchingDesktopSource = formattedSources.find((source) => {
              if (source.type === 'screen') return false
              const sourceTitle = source.name.toLowerCase()

              if (sourceTitle === macTitle) return true

              if (macApp === 'Cursor' && sourceTitle.includes('—') && macTitle.includes('—')) {
                return sourceTitle === macTitle
              }

              if (sourceTitle.includes(macTitle) || macTitle.includes(sourceTitle)) {
                return true
              }

              return false
            })

            if (matchingDesktopSource) {
              realAppNames.set(matchingDesktopSource.name, macApp)
              logger.info(`🔗 Matched: "${matchingDesktopSource.name}" -> App: ${macApp}`)
            }
          }

          // Second pass: add all desktopCapturer windows to the map with correct app names
          formattedSources
            .filter((s) => s.type === 'window')
            .forEach((source) => {
              // Use real app name if available, otherwise fall back to parsing window title
              const realApp = realAppNames.get(source.name)
              let appName = realApp || source.name.split(' - ')[0]

              // Apply Cursor-specific formatting if we know it's actually Cursor
              let displayName = source.name
              if (realApp === 'Cursor') {
                if (source.name.includes(' — ')) {
                  const parts = source.name.split(' — ')
                  if (parts.length >= 2) {
                    const lastPart = parts[parts.length - 1]
                    if (!lastPart.includes('.') && lastPart.length < 30) {
                      displayName = `Cursor - ${lastPart}`
                    }
                  }
                }
              }

              if (!windowsByApp.has(appName)) {
                windowsByApp.set(appName, [])
              }
              windowsByApp.get(appName).push({
                ...source,
                name: displayName, // Use the corrected display name
                appName: appName, // Store the real app name
                fromDesktopCapturer: true
              })
            })

          // Process windows from native API
          for (const window of allWindows) {
            const appName = window.appName

            // Skip Electron's own windows
            if (appName === 'MineContext' || appName === 'Electron') continue

            // Check if we already have windows from this app
            const existingWindows = windowsByApp.get(appName) || []

            // For important apps, always include minimized windows
            const importantApps = [
              'Zoom',
              'zoom.us',
              'Slack',
              'Microsoft Teams',
              'MSTeams',
              'Teams',
              'Discord',
              'Skype',
              'Microsoft PowerPoint',
              'PowerPoint',
              'Keynote',
              'Presentation',
              'Notion',
              'Obsidian',
              'Roam Research',
              'Logseq',
              'Visual Studio Code',
              'Code',
              'Xcode',
              'IntelliJ IDEA',
              'PyCharm',
              'Google Chrome',
              'Safari',
              'Firefox',
              'Microsoft Edge',
              'Figma',
              'Sketch',
              'Adobe Photoshop',
              'Adobe Illustrator',
              'Finder',
              'System Preferences',
              'Activity Monitor'
            ]
            const isImportantApp = window.isImportantApp || importantApps.includes(appName)

            // Check if this specific window already exists
            const windowExists = existingWindows.some((existing) => {
              const existingTitle = existing.name.toLowerCase()
              const currentTitle = `${appName} - ${window.windowTitle}`.toLowerCase()
              return existingTitle === currentTitle
            })

            // Add the window if it doesn't exist or if it's an important app that might be minimized
            if (!windowExists || (isImportantApp && !window.isOnScreen)) {
              // Debug logging for Teams
              if (window.appName.includes('Teams')) {
                logger.info(
                  `🔍 Teams window detection: ${window.appName} - ${window.windowTitle}, isOnScreen: ${window.isOnScreen}, windowExists: ${windowExists}, isImportantApp: ${isImportantApp}`
                )
              }

              // Check if this window was already found by desktopCapturer (meaning it's visible)
              const foundByDesktopCapturer = formattedSources.some((source) => {
                const sourceName = source.name.toLowerCase()
                const windowName = window.appName.toLowerCase()
                return sourceName.includes(windowName) || sourceName.includes('teams')
              })

              // Create a virtual source for this window
              const virtualSource = {
                id: `virtual-window:${window.windowId || Date.now()}-${encodeURIComponent(window.appName)}`,
                name: `${window.appName} - ${window.windowTitle}`,
                type: 'window',
                thumbnail: null, // Will be captured when selected
                appIcon: null,
                isVisible: foundByDesktopCapturer || window.isOnScreen || false,
                isVirtual: true,
                appName: window.appName,
                windowTitle: window.windowTitle,
                windowId: window.windowId
              } as CaptureSource

              // Try to get a real thumbnail using desktopCapturer
              try {
                const electronSources = await desktopCapturer.getSources({
                  types: ['window'],
                  thumbnailSize: { width: 512, height: 288 },
                  fetchWindowIcons: true
                })

                // Try multiple matching strategies to find the window
                let matchingSource: DesktopCapturerSource | undefined = undefined

                // Strategy 1: Exact app name match
                matchingSource = electronSources.find((source) =>
                  source.name.toLowerCase().includes(window.appName.toLowerCase())
                )

                // Strategy 2: Partial match
                if (!matchingSource) {
                  matchingSource = electronSources.find(
                    (source) =>
                      window.appName.toLowerCase().includes(source.name.toLowerCase().split(' ')[0]) ||
                      source.name.toLowerCase().split(' ')[0].includes(window.appName.toLowerCase())
                  )
                }

                // Strategy 3: For specific known apps, try common variations
                if (!matchingSource && window.appName.includes('zoom')) {
                  matchingSource = electronSources.find((source) => source.name.toLowerCase().includes('zoom'))
                }

                if (matchingSource && matchingSource.thumbnail) {
                  virtualSource.thumbnail = matchingSource.thumbnail.toDataURL()
                  virtualSource.appIcon = matchingSource.appIcon ? matchingSource.appIcon.toDataURL() : null
                  logger.info(`Successfully got thumbnail from desktopCapturer for ${window.appName}`)
                } else {
                  logger.info(`No matching desktopCapturer source for ${window.appName}`)
                }
              } catch (captureError: any) {
                logger.error(`desktopCapturer failed for ${window.appName}: ${captureError.message}`)
              }

              if (!virtualSource.thumbnail) {
                // Choose color and icon based on app name
                let bgColor = '#4a4a4a'
                let appIcon = '📱'

                if (window.appName.toLowerCase().includes('zoom')) {
                  bgColor = '#2D8CFF'
                  appIcon = '📹'
                } else if (window.appName.toLowerCase().includes('powerpoint')) {
                  bgColor = '#D24726'
                  appIcon = '📊'
                } else if (window.appName.toLowerCase().includes('notion')) {
                  bgColor = '#000000'
                  appIcon = '📝'
                } else if (window.appName.toLowerCase().includes('slack')) {
                  bgColor = '#4A154B'
                  appIcon = '💬'
                } else if (window.appName.toLowerCase().includes('teams')) {
                  bgColor = '#6264A7'
                  appIcon = '👥'
                } else if (window.appName.toLowerCase().includes('chrome')) {
                  bgColor = '#4285F4'
                  appIcon = '🌐'
                } else if (window.appName.toLowerCase().includes('word')) {
                  bgColor = '#2B579A'
                  appIcon = '📄'
                } else if (window.appName.toLowerCase().includes('excel')) {
                  bgColor = '#217346'
                  appIcon = '📊'
                } else if (window.appName.toLowerCase().includes('wechat')) {
                  bgColor = '#07C160'
                  appIcon = '💬'
                }

                // Create SVG placeholder
                const svg = `
                <svg width="256" height="144" xmlns="http://www.w3.org/2000/svg">
                  <rect width="256" height="144" fill="${bgColor}"/>
                  <text x="128" y="60" font-family="Arial, sans-serif" font-size="32" text-anchor="middle" fill="white">${appIcon}</text>
                  <text x="128" y="85" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="white">${window.appName}</text>
                  <text x="128" y="100" font-family="Arial, sans-serif" font-size="10" text-anchor="middle" fill="#cccccc">Hidden</text>
                </svg>
              `

                virtualSource.thumbnail = `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`
              }

              formattedSources.push(virtualSource)
            }
          }
        } catch (macError: any) {
          logger.error('Error getting additional windows from macOS:', macError)
          // Continue with just the desktopCapturer sources
        }
      }

      return {
        success: true,
        sources: formattedSources
      }
    } catch (error: any) {
      logger.error('Failed to get capture sources:', error)
      return {
        success: false,
        error: error.message,
        sources: [] as CaptureSource[]
      }
    }
  }
  async takeSourceScreenshotTools(sourceId: string) {
    try {
      // Check permissions on macOS
      if (process.platform === 'darwin') {
        const hasScreenPermission = systemPreferences.getMediaAccessStatus('screen')
        if (hasScreenPermission !== 'granted') {
          const permissionGranted = await systemPreferences.askForMediaAccess('camera')
          if (!permissionGranted) {
            throw new Error(
              'Screen recording permission not granted. Please grant screen recording permissions in System Preferences > Security & Privacy > Screen Recording and restart the application.'
            )
          }
        }
      }

      // Handle virtual windows (minimized or on other spaces)
      if (sourceId.startsWith('virtual-window:')) {
        // Extract app name from the source ID
        const appNameMatch = sourceId.match(/virtual-window:\d+-(.+)$/)
        const appName = appNameMatch ? decodeURIComponent(appNameMatch[1]) : null

        // Declare matchingSource in the correct scope
        let matchingSource: DesktopCapturerSource | undefined = undefined

        // First, quickly check if the app might be visible on current desktop
        const quickSources = await desktopCapturer.getSources({
          types: ['window'],
          thumbnailSize: { width: 256, height: 144 }, // Small size for quick check
          fetchWindowIcons: false
        })

        // Quick check if app is likely on current desktop
        const quickMatch = quickSources.find((source) => {
          const name = source.name.toLowerCase()
          const appLower = appName?.toLowerCase() || ''
          return (
            name.includes(appLower) ||
            (appLower.includes('powerpoint') && (name.includes('powerpoint') || name.includes('ppt'))) ||
            (appLower.includes('wechat') && name.includes('weixin')) ||
            (appLower.includes('chrome') && name.includes('chrome'))
          )
        })

        if (quickMatch) {
          // Disabled to reduce log spam during frequent captures
          // safeLog.log(`✅ ${appName} found on current desktop, getting high-quality thumbnail`);

          // Get high-quality capture since we know it's visible
          try {
            const sources = await desktopCapturer.getSources({
              types: ['window'],
              thumbnailSize: { width: 1920, height: 1080 },
              fetchWindowIcons: true
            })

            // Find the matching source again with better quality
            matchingSource = sources.find((s) => s.id === quickMatch.id)

            if (matchingSource) {
              return {
                success: true,
                source: matchingSource
              }
            }
          } catch (highQualityError: any) {
            logger.error(`Failed to get high-quality capture: ${highQualityError.message}`)
          }
        } else {
          // App not on current desktop
        }

        // Check variable state

        // Try Python-free native capture helper for screen capture
        if (this.nativeCaptureHelper && this.nativeCaptureHelper.isRunning && appName) {
          logger.info(`Attempting Python-free screen capture for ${appName}`)
          try {
            const captureResult = await this.nativeCaptureHelper.captureScreen(0)
            logger.log(`[Python Capture] captureResult: ${captureResult.success}, data: ${captureResult.data?.length}`)
            logger.log(Buffer.from(captureResult.data as any, 'binary'))
            if (captureResult.success && captureResult.data) {
              return {
                success: true,
                source: {
                  id: `python-free-screen-capture:${appName}`,
                  name: `${appName} (Screen Capture - Python Free)`,
                  thumbnail: {
                    toPNG: () => captureResult.data,
                    isEmpty: () => false
                  }
                },
                sourceName: `${appName} (Screen Capture - Python Free)`,
                captureMethod: 'python_free_screen'
              }
            } else {
              logger.error(`❌ Python-free screen capture failed for ${appName}: ${captureResult.error}`)
            }
          } catch (nativeError: any) {
            const message = nativeError instanceof Error ? nativeError.message : 'An unknown error occurred.'
            logger.error(`❌ Python-free capture error for ${appName}: ${message}`)
          }
        }

        // Fallback: Try advanced macOS capture methods for cross-desktop window capture
        if (appName && process.platform === 'darwin') {
          try {
            const allWindows = await getAllWindows()
            const targetWindow = allWindows.find(
              (w) =>
                w.appName.toLowerCase() === appName.toLowerCase() ||
                w.appName.toLowerCase().includes(appName.toLowerCase()) ||
                appName.toLowerCase().includes(w.appName.toLowerCase())
            )

            if (targetWindow && targetWindow.windowId) {
              logger.log(`[Python Capture] Capturing window ${targetWindow.windowId} for app ${appName}`)
              try {
                const captureResult = await new Promise(async (resolve, reject) => {
                  const basePath = app.isPackaged
                    ? path.join(process.resourcesPath, 'bin', 'window_capture')
                    : path.join(__dirname, '../..', 'externals/python/window_capture/dist', 'window_capture')
                  const exePath = path.join(basePath, 'window_capture')
                  const py = spawn(exePath, [
                    JSON.stringify({
                      appName: 'Notion',
                      windowId: 67890
                    })
                  ])

                  let output = ''
                  let error = ''

                  py.stdout.on('data', (data) => (output += data.toString()))
                  py.stderr.on('data', (data) => (error += data.toString()))

                  py.on('close', (code) => {
                    if (code === 0 && output.trim() && !output.startsWith('ERROR:')) {
                      try {
                        const base64Data = output.trim()
                        logger.log(`[Python Capture] Raw base64 data length: ${base64Data}`)
                        const imageBuffer = Buffer.from(base64Data, 'binary')
                        resolve(imageBuffer)
                      } catch (parseError: any) {
                        reject(new Error(`Failed to parse image data: ${parseError.message}`))
                      }
                    } else {
                      reject(new Error(`Python capture failed: ${error || output}`))
                    }
                  })

                  py.on('error', reject)
                })

                if (captureResult && (captureResult as Buffer).length > 1000) {
                  return {
                    success: true,
                    source: { thumbnail: { captureResult, toPNG: () => captureResult, isEmpty: () => false } },
                    sourceName: appName,
                    isCGWindowCapture: true
                  }
                }
              } catch (cgWindowError: any) {
                logger.error(`❌ Python fallback capture failed for ${appName}: ${cgWindowError.message}`)
              }
            }
          } catch (outerError: any) {
            logger.error(`❌ Cross-desktop capture failed for ${appName}: ${outerError.message}`)
          }
        }

        // Fallback: Create a more informative placeholder image for failed capture
        logger.info(`Creating placeholder for virtual window: ${appName}`)

        // Convert SVG to PNG using a minimal PNG fallback for now
        const minimalPng = Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
          'binary'
        )

        return {
          success: true,
          source: { thumbnail: { minimalPng, toPNG: () => minimalPng, isEmpty: () => false } },
          sourceName: appName || 'Virtual Window',
          isPlaceholder: true,
          placeholderReason: 'Window not accessible - may be minimized or on another desktop'
        }
      } else if (sourceId.startsWith('window:')) {
        const sources = await desktopCapturer.getSources({
          types: ['window'],
          thumbnailSize: { width: 1920, height: 1080 },
          fetchWindowIcons: true
        })

        const source = sources.find((s) => s.id === sourceId)
        if (!source) {
          throw new Error(`Window with ID ${sourceId} not found`)
        }

        return {
          success: true,
          source,
          sourceName: source.name
        }
      } else {
        // For screens, use the regular approach
        const sources = await desktopCapturer.getSources({
          types: ['screen'],
          thumbnailSize: { width: 1920, height: 1080 }
        })

        const source = sources.find((s) => s.id === sourceId)
        if (!source) {
          throw new Error(`Screen with ID ${sourceId} not found`)
        }

        return {
          success: true,
          source,
          sourceName: source.name
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message
      }
    }
  }
  async listDisplays() {
    try {
      const displays = await screenshot.listDisplays()
      return {
        success: true,
        displays: displays.map((display, index) => ({
          id: display.id,
          index: index,
          name: display.name || `Display ${index + 1}`,
          bounds: display.bounds
        }))
      }
    } catch (error: any) {
      logger.error('Failed to list displays:', error)
      return {
        success: false,
        error: error.message,
        displays: []
      }
    }
  }
  async takeScreenshotOfDisplay(displayId = 0) {
    try {
      const displays = await screenshot.listDisplays()
      if (displayId >= displays.length) {
        throw new Error(`Display ${displayId} not found. Available displays: ${displays.length}`)
      }

      const imgBuffer = await screenshot({ screen: displays[displayId].id })

      return {
        success: true,
        source: imgBuffer,
        size: imgBuffer.length,
        displayId: displayId
      }
    } catch (error: any) {
      logger.error('Failed to take screenshot of display:', error)
      return {
        success: false,
        error: error.message
      }
    }
  }
  async takeScreenshotTools() {
    try {
      // Try to take screenshot with better error handling
      try {
        const imgBuffer = await screenshot()
        return {
          success: true,
          source: imgBuffer,
          size: imgBuffer.length
        }
      } catch (screenshotError: any) {
        logger.error('Screenshot capture failed:', screenshotError)
        return {
          success: false,
          error: screenshotError.message
        }
      }
    } catch (error: any) {
      logger.error('Failed to take screenshot:', error)
      return {
        success: false,
        error: error.message
      }
    }
  }
  async getVisibleSourcesTools(sourceIds?: string[]) {
    try {
      if (sourceIds && sourceIds.length > 0) {
        logger.info('Checking active/focused apps for source IDs:', sourceIds)

        // Enhanced multi-space/multi-screen visibility detection
        let activeAppsOnAllSpaces: string[] = []
        if (process.platform === 'darwin') {
          try {
            const execAsync = promisify(exec)

            // Get apps that have visible windows on ANY space (not just current)
            const { stdout: visibleAppsStdout } = await execAsync(`osascript -e '
            tell application "System Events"
              set visibleApps to {}
              repeat with p in (every application process)
                try
                  -- Check if app has any windows
                  if (count of windows of p) > 0 then
                    set end of visibleApps to (name of p as string)
                  end if
                end try
              end repeat
              return my list_to_string(visibleApps, ",")
            end tell
            
            on list_to_string(lst, delim)
              set AppleScript's text item delimiters to delim
              set str to lst as string
              set AppleScript's text item delimiters to ""
              return str
            end list_to_string
          '`)

            if (visibleAppsStdout && visibleAppsStdout.trim()) {
              activeAppsOnAllSpaces = visibleAppsStdout
                .trim()
                .toLowerCase()
                .split(',')
                .map((app) => app.trim())
              logger.info(`Apps with windows on all spaces: [${activeAppsOnAllSpaces.join(', ')}]`)
            }

            // Also get the frontmost app on current space for additional context
            const { stdout: frontmostStdout } = await execAsync(
              `osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true'`
            )
            const frontmostApp = frontmostStdout.trim().toLowerCase()
            logger.info(`Frontmost app on current space: "${frontmostApp}"`)
          } catch (error: any) {
            logger.error('Could not get apps with windows:', error.message)
            // Fallback to assume all apps are visible
            activeAppsOnAllSpaces = []
          }
        }

        // Also get visible sources for fallback
        const visibleSources = await desktopCapturer.getSources({
          types: ['window', 'screen'],
          thumbnailSize: { width: 1, height: 1 },
          fetchWindowIcons: false
        })

        const results = sourceIds.map((id) => {
          let isVisible = false
          let name = 'Unknown'

          if (id.startsWith('virtual-window:')) {
            const appNameMatch = id.match(/virtual-window:\d+-(.+)$/)
            if (appNameMatch) {
              name = decodeURIComponent(appNameMatch[1])

              // Enhanced visibility check: app is visible if it has windows on ANY space
              if (activeAppsOnAllSpaces.length > 0) {
                const appNameLower = name.toLowerCase()
                const hasWindowsOnAnySpace = activeAppsOnAllSpaces.some((activeApp) => {
                  return (
                    activeApp.includes(appNameLower) ||
                    appNameLower.includes(activeApp) ||
                    (appNameLower === 'msteams' && activeApp.includes('teams')) ||
                    (appNameLower === 'microsoft teams' && activeApp.includes('teams')) ||
                    (appNameLower === 'wechat' && (activeApp.includes('wechat') || activeApp.includes('weixin'))) ||
                    (appNameLower === 'google chrome' && activeApp.includes('chrome')) ||
                    (appNameLower === 'visual studio code' &&
                      (activeApp.includes('code') || activeApp.includes('visual studio'))) ||
                    (appNameLower === 'microsoft powerpoint' &&
                      (activeApp.includes('powerpoint') || activeApp.includes('microsoft powerpoint'))) ||
                    (appNameLower === 'microsoft word' &&
                      (activeApp.includes('word') || activeApp.includes('microsoft word'))) ||
                    (appNameLower === 'microsoft excel' &&
                      (activeApp.includes('excel') || activeApp.includes('microsoft excel')))
                  )
                })

                if (hasWindowsOnAnySpace) {
                  isVisible = true
                  logger.info(`Virtual window has windows on some space: ${id} -> ${name}`)
                } else {
                  logger.info(`Virtual window has no windows on any space: ${id} -> ${name}`)
                }
              } else {
                // Fallback: if we can't detect apps with windows, assume visible
                isVisible = true
                logger.info(`Virtual window assumed visible (no space detection): ${id} -> ${name}`)
              }
            }
          } else {
            // For regular window IDs, check if they're actually visible
            const visibleSource = visibleSources.find((s) => s.id === id)
            if (visibleSource) {
              isVisible = true
              name = visibleSource.name
              logger.info(`Regular window found visible: ${id} -> ${name}`)
            } else {
              logger.info(`Regular window NOT visible: ${id}`)
            }
          }

          return { id, isVisible, name }
        })

        return { success: true, sources: results }
      } else {
        const visibleSources = await desktopCapturer.getSources({
          types: ['window', 'screen'],
          thumbnailSize: { width: 1, height: 1 },
          fetchWindowIcons: false
        })

        const allVisible = visibleSources.map((s) => ({
          id: s.id,
          name: s.name,
          isVisible: true
        }))

        return { success: true, sources: allVisible }
      }
    } catch (error: any) {
      logger.error('Error checking source visibility:', error)
      return { success: false, error: error.message }
    }
  }
}

export { CaptureSourcesTools }
