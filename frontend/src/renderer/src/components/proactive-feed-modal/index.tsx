// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { Modal, Button } from '@arco-design/web-react'
import { FC, ReactNode } from 'react'
import { MarkdownContent } from '../ai-assistant'
import titleBg from './assets/bg.png'
interface ProactiveFeedModalProps {
  visible: boolean
  onCancel: () => void
  content?: ReactNode
  time?: ReactNode
}

const ProactiveFeedModal: FC<ProactiveFeedModalProps> = (props) => {
  const { visible, onCancel, content } = props

  // Modal header (including icon, title, subtitle)
  const modalHeader = (
    <div
      className={`bg-[url('${titleBg}')] !bg-no-repeat w-full h-[76px] !bg-cover !bg-center rounded-[8px] overflow-hidden flex items-center`}
      style={{ background: `url(${titleBg})` }}>
      <div className="ml-[118px]">
        <div
          className="text-[20px] leading-[22px] bg-[linear-gradient(271.9deg,_#C296FF_-23.68%,_#FF875F_100.99%)]
  bg-clip-text text-transparent font-bold">
          Proactive Feed
        </div>
        <div className="text-[12px] leading-[20px] text-[#6e718c]">Here’s some insights you should konw</div>
      </div>
    </div>
  )

  // Modal content area (tutorial text)
  const modalContent = (
    <div className="mt-4 h-full overflow-x-hidden overflow-y-auto">
      <MarkdownContent content={String(content || ``)} />
    </div>
  )

  // Modal footer (confirmation button)
  const modalFooter = (
    <div className="flex justify-end p-4">
      <Button
        type="primary"
        onClick={onCancel}
        className="flex w-[116px] px-4 py-[5px] justify-center items-center gap-2 rounded-md"
        style={{
          backgroundColor: '#0B0B0F'
        }}>
        I got it
      </Button>
    </div>
  )

  return (
    <Modal
      visible={visible}
      title={modalHeader}
      footer={modalFooter}
      onCancel={onCancel}
      className="!w-[700px] !h-[588px] [&_.arco-modal-header]:!h-auto [&_.arco-modal-header]:!px-0 px-[20px] pt-[16px] pb-[20px] [&_>_div]:nth-2:flex [&_>_div]:nth-2:flex-col [&_>_div]:nth-2:h-full [&_.arco-modal-content]:!flex-1 [&_.arco-modal-content]:!p-0 [&_.arco-modal-footer]:!p-0 [&_.arco-modal-content]:!overflow-y-hidden [&_.arco-modal-footer]:!h-auto"
      closable={false} // Hide the default "Close" button, only keep the custom "I got it"
    >
      {modalContent}
    </Modal>
  )
}

export { ProactiveFeedModal }
