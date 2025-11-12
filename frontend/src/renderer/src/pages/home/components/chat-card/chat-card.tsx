import { useMemoizedFn, useMount, useRequest } from 'ahooks'
import { CardLayout } from '../layout'
import { ConversationResponse, conversationService } from '@renderer/services/conversation-service'
import { isEmpty } from 'lodash'
import chatHistoryIcon from '@renderer/assets/icons/ai-assistant/chat-history.svg'
import { Typography } from '@arco-design/web-react'
import { useAppDispatch } from '@renderer/store'
import { setActiveConversationId, toggleCreationAiAssistant, toggleHomeAiAssistant } from '@renderer/store/chat-history'
import { useNavigation } from '@renderer/hooks/use-navigation'
import { formatRelativeTime } from '@renderer/utils/time'
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
  const dispatch = useAppDispatch()
  const { navigateToMainTab, navigateToVault } = useNavigation()
  const handleNavigation = useMemoizedFn((conversation: ConversationResponse) => {
    const from = conversation.page_name || 'home'
    const id = conversation.id
    dispatch(setActiveConversationId(id))
    const metadata = conversation.metadata || '{}'
    if (from === 'home') {
      dispatch(toggleHomeAiAssistant(true))
      navigateToMainTab('home', '/')
    } else if (from === 'creation') {
      dispatch(toggleCreationAiAssistant(true))
      try {
        const parsedMetadata = JSON.parse(metadata)
        const document_id = parsedMetadata.document_id
        navigateToVault(document_id)
      } catch (error) {}
    }
  })
  return (
    <CardLayout title="Recent chat" emptyText="No chats in the latest 7 days. " isEmpty={isEmpty(conversationList)}>
      {(conversationList || [])?.map((conversation) => (
        <div className="flex items-center cursor-pointer justify-between group w-full hover:bg-[#F7F8FD] rounded-[6px] py-[5px] px-[4px]">
          <div
            className=" flex items-center gap-[6px]  "
            key={conversation.id}
            onClick={() => handleNavigation(conversation)}>
            <img src={chatHistoryIcon} className="block" />
            <Typography.Text className="!my-0 !flex-1 !text-[13px] !leading-[22px] !font-normal" ellipsis={{ rows: 1 }}>
              {conversation.title || 'Untitled Conversation'}
            </Typography.Text>
            {conversation.updated_at && (
              <span className="flex text-[#AEAFC2]  items-center text-[11px] font-normal leading-[22px] opacity-0 group-hover:opacity-100">
                {formatRelativeTime(conversation.updated_at)}
              </span>
            )}
          </div>
          <div className="flex items-center">
            {/* View button - hidden by default, shown on hover */}
            <button className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-[#7075FF] font-pingfang-sc text-[12px] font-medium leading-[20px] tracking-[0.036px] cursor-pointer">
              View
            </button>
          </div>
        </div>
      ))}
    </CardLayout>
  )
}
export { ChatCard }
