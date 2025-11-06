import { FC } from 'react'
import addChatIcon from '@renderer/assets/icons/ai-assistant/add-chat.svg'
import chatHistoryIcon from '@renderer/assets/icons/ai-assistant/chat-history.svg'
import { Button, Space, Divider, Popover } from '@arco-design/web-react'
import { IconClose } from '@arco-design/web-react/icon'
import { useMemoizedFn, useRequest } from 'ahooks'
import { conversationService } from '@renderer/services/conversation-service'
import { ChatHistoryList } from './chat-history-list'
export interface AIAssistantHeaderProps {
  onClose: () => void
  startNewConversation: () => void
  conversationId: number
  handleGetMessages?: (conversationId: number) => void
  pageName: string
}
const AIAssistantHeader: FC<AIAssistantHeaderProps> = (props) => {
  const { onClose, startNewConversation, handleGetMessages, pageName } = props
  const {
    runAsync: getConversationList,
    data: conversationList,
    refresh: refreshConversationList
  } = useRequest(
    async () => {
      const res = await conversationService.getConversationList({
        limit: 30,
        offset: 0,
        page_name: pageName,
        status: 'active'
      })
      return res.items || []
    },
    { manual: true }
  )
  const handleVisibleChange = useMemoizedFn((visible: boolean) => {
    if (visible) {
      getConversationList()
    }
  })
  return (
    <div className="flex items-center justify-between px-[16px] border-b border-[#F0F2FA]">
      <div
        className="flex items-center font-medium text-[#5252FF] cursor-pointer"
        onClick={startNewConversation}
        style={{ padding: '12px 16px' }}>
        <img src={addChatIcon} alt="add-chat" className="w-[16px] h-[16px] mr-[6px]" />
        New chat
      </div>
      <Space>
        <Popover
          position="br"
          content={
            <ChatHistoryList
              conversationList={conversationList || []}
              handleGetMessages={handleGetMessages}
              onConversationUpdate={getConversationList}
              refreshConversationList={refreshConversationList}
            />
          }
          trigger={['click', 'hover']}
          onVisibleChange={handleVisibleChange}>
          <div className="flex items-center justify-center w-[32px] h-[32px] hover:bg-[#F6F7FA] rounded-[6px] cursor-pointer">
            <img src={chatHistoryIcon} className="w-[14px] h-[14px]" />
          </div>
        </Popover>

        <Divider type="vertical" className="!mx-0" />
        <Button type="text" icon={<IconClose />} onClick={onClose} className="text-[#86909c]" />
      </Space>
    </div>
  )
}
export { AIAssistantHeader }
