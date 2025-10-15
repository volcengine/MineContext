// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

/* eslint-disable @typescript-eslint/no-explicit-any */
import { desktopCapturer } from 'electron'
import { exec } from 'child_process'
import { promisify } from 'util'
import { getLogger } from '@shared/logger/main'

const logger = getLogger('getVisibleSource')
interface SourceVisibilityInfo {
  id: string
  isVisible: boolean
  name: string
}

export interface GetVisibleSourceResult {
  success: boolean
  sources?: SourceVisibilityInfo[]
  error?: string
}

const getVisibleSource: (sourceIds: string[]) => Promise<GetVisibleSourceResult> = async (sourceIds) => {
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
          logger.info('Could not get apps with windows:', error.message)
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
      // Return all available sources
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

export { getVisibleSource }
