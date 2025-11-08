import { FC } from 'react'
import logoImage from '@renderer/assets/icons/ai-assistant/logo.png'

import { ChatHistoryListItem } from './chat-history-list-item'
export interface ChatHistoryListProps {
  conversationList: any[]
  handleGetMessages?: (conversationId: number) => void
  onConversationUpdate?: () => void
  refreshConversationList?: () => void
}

const ChatHistoryList: FC<ChatHistoryListProps> = (props) => {
  const { conversationList, refreshConversationList, handleGetMessages } = props

  if (conversationList.length === 0) {
    return (
      <div className="w-[270px] p-4 text-center text-gray-500 flex items-center justify-center flex-col">
        <img src={logoImage} alt="No chat history" className="w-[62px] h-[46px]" />
        <div className="text-[12px] leading-[22px]">Ops...No chats yet</div>
      </div>
    )
  }
  return (
    <div className="w-[270px] h-[70%] px-[16px] py-[20px]">
      <div className="text-[14px] leading-[22px] text-[#0c0d0e] font-medium mb-[12px]">Recent chats</div>
      <div className="overflow-x-hidden overflow-y-auto min-h-[400px] ">
        {conversationList.map((conversation) => (
          <ChatHistoryListItem
            conversation={conversation}
            key={conversation.id}
            refreshConversationList={refreshConversationList}
            handleGetMessages={handleGetMessages}
          />
        ))}
      </div>
    </div>
  )
}
export { ChatHistoryList }
