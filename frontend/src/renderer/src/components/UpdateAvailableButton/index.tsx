import { useState, useEffect } from 'react'
import rocketSvg from '@renderer/assets/icons/rocket.svg'
import { UpdateInfo } from 'electron-updater'
import { IpcChannel } from '@shared/IpcChannel'
import { debounce } from 'lodash'

export default function UpdateAvailableButton() {
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null)
  const [isDownloaded, setIsDownloaded] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
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
      <div
      className="relative w-full flex items-center bg-[#FFFEF9] justify-center rounded-[6px] px-2 py-1.5 bg-gradient-to-tr hover:from-[rgba(246,236,255,0.43)] to-[#FFFEF9] transition cursor-pointer"
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <img src={rocketSvg} className="w-3 h-3" />
      {/* 文本内容 */}
      <span className="text-[#3F3F51] text-[12px] ml-1">
        {!isHovered ? 'Update available' : 'Restart to update'}
      </span>

      {/* 版本号 */}
      {
        !isHovered ? <span className="pl-2 font-['Roboto'] text-[10px] text-[#AEAFC2]">
        {updateInfo.version}
      </span> : null
      }

      {/* 蓝色提示点 */}
      <span className="w-1.5 h-1.5 bg-[#5252FF] rounded-full absolute top-[-1px] right-[-1px]"></span>
    </div>
  );
}
