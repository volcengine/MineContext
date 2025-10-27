import { useState, useEffect } from 'react'
import { RefreshCw } from "lucide-react"
import { UpdateInfo } from 'electron-updater'
import { IpcChannel } from '@shared/IpcChannel'
import { useNotification } from '@renderer/context/NotificationProvider'
import { debounce } from 'lodash'

export default function UpdateAvailableButton() {
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null)
  const [isDownloaded, setIsDownloaded] = useState(false)
  const { open } = useNotification()
  useEffect(() => {
    ;(async () => {
      const { updateInfo: _updateInfo } = await window.api.checkForUpdate()
      console.log("checkForUpdate", _updateInfo)
      setUpdateInfo(_updateInfo)
    })()
  }, [])

  useEffect(() => {
    if (!window.electron) return

    const ipcRenderer = window.electron.ipcRenderer

    const f1 = ipcRenderer.on(IpcChannel.UpdateDownloaded, () => {
      console.log("UpdateDownloaded")
      setIsDownloaded(true)
    })

    const f2 = ipcRenderer.on(IpcChannel.UpdateError, (_, err) => {
      console.error("UpdateError", err)
      open.error?.({
        title: 'update error',
        content: err.message
      })
    })
    return () => {
      f1()
      f2()
    }
  }, [])

  const handleClick = debounce(
    () => {
      window.api.quitAndInstall()
    },
    2000,
    { leading: true, trailing: false }
  )

  if (!updateInfo || !isDownloaded) return null
  return (
    <div className="relative w-full flex items-center space-x-2 bg-white/60 backdrop-blur-md border border-white/40 shadow-sm rounded-xl px-2 py-4 hover:shadow-md transition cursor-pointer" onClick={handleClick}>
      {/* 刷新图标（旋转动画） */}
      <RefreshCw className="w-3 h-3 text-gray-500 animate-spin-slow" />

      {/* 文本内容 */}
      <span className="text-gray-800 text-[11px] font-medium ml-1">
        Update available
      </span>

      {/* 版本号 */}
      <span className="text-gray-500 text-[10px] bg-gray-100 rounded-sm px-2 py-0.5">
        {updateInfo.version}
      </span>

      {/* 蓝色提示点 */}
      <span className="w-2 h-2 bg-blue-500 rounded-full ml-1 absolute top-[-2px] right-[-2px]"></span>
    </div>
  );
}
