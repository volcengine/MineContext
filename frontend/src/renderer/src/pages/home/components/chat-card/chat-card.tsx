import { useMount, useRequest } from 'ahooks'
import { CardLayout } from '../layout'
import { conversationService } from '@renderer/services/conversation-service'
import { isEmpty } from 'lodash'
import chatHistoryIcon from '@renderer/assets/icons/ai-assistant/chat-history.svg'
import { Typography } from '@arco-design/web-react'
const ChatCard = () => {
  const { data: conversationList, run } = useRequest(
    async () => {
      const res = await conversationService.getConversationList({
        limit: 30,
        offset: 0,
        status: 'active'
      })
      return res.items || []
    },
    { manual: true }
  )
  useMount(() => {
    run()
  })
  return (
    <CardLayout title="Recent chat" emptyText="No chats in the latest 7 days. " isEmpty={isEmpty(conversationList)}>
      {(conversationList || [])?.map((conversation) => (
        <div className="cursor-pointer flex items-center gap-[6px]">
          <img src={chatHistoryIcon} className="block" />
          <Typography.Title className="!my-0 !flex-1 !text-[13px] !leading-[22px]" ellipsis={{ rows: 1 }}>
            {conversation.title || 'Untitled Conversation'}
          </Typography.Title>
        </div>
      ))}
    </CardLayout>
  )
}
export { ChatCard }
