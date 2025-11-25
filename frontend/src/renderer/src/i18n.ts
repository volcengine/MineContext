import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Locale resources
import enUS from '../../locales/en-US/translation.json'
import zhCN from '../../locales/zh-CN/translation.json'

// Initialize callback to be called when i18n is ready
type I18nReadyCallback = () => void
const readyCallbacks: I18nReadyCallback[] = []

export const onI18nReady = (callback: I18nReadyCallback): void => {
  if (i18n.isInitialized) {
    callback()
  } else {
    readyCallbacks.push(callback)
  }
}

const resources = {
  'en-US': {
    translation: enUS
  },
  'zh-CN': {
    translation: zhCN
  }
}

i18n
  .use(initReactI18next)
  .init({
    debug: true,
    lng: 'en-US',
    fallbackLng: 'en-US',
    resources,
    interpolation: {
      escapeValue: false, // not needed for react as it escapes by default
    },
    react: {
      useSuspense: true,
    },
  })
  .then(() => {
    console.log('[i18n] Renderer i18n initialized successfully')
    // Execute all ready callbacks
    readyCallbacks.forEach(callback => callback())
    readyCallbacks.length = 0
  })
  .catch((error) => {
    console.error('[i18n] Renderer i18n initialization failed:', error)
  })

export default i18n
