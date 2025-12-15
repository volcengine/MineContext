import i18next from 'i18next'
import Backend from 'i18next-fs-backend'
import path from 'path'
import { app } from 'electron'

const isDev = !app.isPackaged

const loadPath = isDev
  ? path.join(__dirname, '../../src/locales/{{lng}}/{{ns}}.json')
  : path.join(process.resourcesPath, 'locales/{{lng}}/{{ns}}.json')

// Initialize callback to be called when i18n is ready
type I18nReadyCallback = () => void
const readyCallbacks: I18nReadyCallback[] = []

export const onI18nReady = (callback: I18nReadyCallback): void => {
  if (i18next.isInitialized) {
    callback()
  } else {
    readyCallbacks.push(callback)
  }
}

i18next
  .use(Backend)
  .init({
    fallbackLng: 'en-US',
    ns: ['translation'],
    defaultNS: 'translation',
    backend: {
      loadPath
    },
    interpolation: {
      escapeValue: false
    }
  })
  .then(() => {
    console.log('[i18n] Main process i18n initialized successfully')
    console.log(`[i18n] Locale files loaded from: ${loadPath}`)
    // Execute all ready callbacks
    readyCallbacks.forEach((callback) => callback())
    readyCallbacks.length = 0
  })
  .catch((error) => {
    console.error('[i18n] Main process i18n initialization failed:', error)
  })

export default i18next
