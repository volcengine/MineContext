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
