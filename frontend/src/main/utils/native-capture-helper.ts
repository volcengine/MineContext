// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import * as nodeScreenshots from 'node-screenshots'
import { getLogger } from '@shared/logger/main'

const logger = getLogger('NativeCaptureHelper')

class NativeCaptureHelper {
  public isRunning: boolean = false
  public screenshots: typeof nodeScreenshots | null = null

  constructor() {}

  async initialize(): Promise<void> {
    logger.info('Initializing Native Capture Helper (Pure JavaScript)...')

    try {
      // Import node-screenshots dynamically
      this.screenshots = nodeScreenshots

      // Test that the module works
      if (!this.screenshots) {
        throw new Error('Failed to load node-screenshots module.')
      }
      const monitors = this.screenshots.Monitor.all()
      logger.info(`[Native Helper] Found ${monitors.length} monitor(s)`)

      this.isRunning = true
      logger.info('✅ Native Capture Helper initialized successfully (Python-free!)')
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'An unknown error occurred.'
      throw new Error(`Native capture helper failed to initialize: ${message}`)
    }
  }

  // High-level methods using pure JavaScript

  async getAllWindows(): Promise<any[]> {
    if (!this.isRunning) {
      throw new Error('Helper not initialized')
    }

    try {
      // This is a simplified implementation. For full window management,
      // a native addon or a different approach would be needed.
      logger.info('[Native Helper] Using simplified window detection (visible windows only)')

      // Return empty for now. The main focus is screen capture.
      // Individual window capture will fall back to desktopCapturer in electron.js
      return []
    } catch (error: unknown) {
      logger.error('Failed to get windows from native helper:', error)
      return []
    }
  }

  async captureWindow(windowId: string | number): Promise<{ success: boolean; error: string }> {
    if (!this.isRunning) {
      throw new Error('Helper not initialized')
    }

    try {
      logger.info(`[Native Helper] Pure JS window capture not supported for windowId ${windowId}`)

      // For a pure JavaScript solution, we can't capture specific windows by ID.
      // This will gracefully fail and let the caller fall back to other methods.
      return {
        success: false,
        error: 'Pure JavaScript helper does not support individual window capture by ID'
      }
    } catch (error: unknown) {
      logger.error(`Failed to capture window ${windowId}:`, error)
      const message = error instanceof Error ? error.message : 'An unknown error occurred.'
      return {
        success: false,
        error: message
      }
    }
  }

  async captureScreen(
    monitorIndex: number = 0
  ): Promise<{ success: boolean; data?: Buffer; size?: number; error?: string }> {
    if (!this.isRunning || !this.screenshots) {
      throw new Error('Helper not initialized or screenshots module not loaded')
    }

    try {
      logger.info(`[Native Helper] Capturing screen ${monitorIndex} using node-screenshots`)

      const monitors = this.screenshots.Monitor.all()
      if (monitorIndex >= monitors.length) {
        return {
          success: false,
          error: `Monitor ${monitorIndex} not found. Available monitors: ${monitors.length}`
        }
      }

      const monitor = monitors[monitorIndex]
      const image = monitor.captureImageSync()
      const pngBuffer = image.toPngSync()

      logger.info(`[Native Helper] Screen capture successful, size: ${pngBuffer.length} bytes`)

      return {
        success: true,
        data: pngBuffer,
        size: pngBuffer.length
      }
    } catch (error: unknown) {
      logger.error(`Failed to capture screen ${monitorIndex}:`, error)
      const message = error instanceof Error ? error.message : 'An unknown error occurred.'
      return {
        success: false,
        error: message
      }
    }
  }

  async captureApp(appName: string): Promise<{ success: boolean; data?: Buffer; size?: number; error?: string }> {
    if (!this.isRunning) {
      throw new Error('Helper not initialized')
    }

    try {
      logger.info(`[Native Helper] Pure JS app capture for: ${appName}`)
      logger.info(`[Native Helper] Note: Individual app capture not supported, falling back to screen capture`)

      // Since we can't capture individual apps with node-screenshots,
      // we'll capture the primary screen as a fallback.
      // The main Electron code will handle specific window capture via desktopCapturer.

      return await this.captureScreen(0) // Capture primary monitor
    } catch (error: unknown) {
      logger.error(`Failed to capture app ${appName}:`, error)
      const message = error instanceof Error ? error.message : 'An unknown error occurred.'
      return {
        success: false,
        error: message
      }
    }
  }

  async shutdown(): Promise<void> {
    if (this.isRunning) {
      logger.info('Shutting down native capture helper')
      this.isRunning = false
    }
  }
}

export { NativeCaptureHelper }
