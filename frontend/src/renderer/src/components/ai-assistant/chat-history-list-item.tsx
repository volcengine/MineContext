import { FC, useState } from 'react'

import { Typography, Trigger, Modal, Form, Input } from '@arco-design/web-react'
import { IconDelete } from '@arco-design/web-react/icon'
import { useMemoizedFn, useRequest } from 'ahooks'
import { conversationService } from '@renderer/services/conversation-service'
import chatHistoryIcon from '@renderer/assets/icons/ai-assistant/chat-history.svg'
export interface ChatHistoryListItemProps {
  conversation: any
  refreshConversationList?: () => void
  handleGetMessages?: (conversationId: number) => void
}

const ChatHistoryListItem: FC<ChatHistoryListItemProps> = (props) => {
  const { conversation, refreshConversationList, handleGetMessages } = props
  const [renameVisible, setRenameVisible] = useState(false)
  const [form] = Form.useForm()
  const { run: updateConversationTitle } = useRequest(conversationService.updateConversationTitle, { manual: true })
  const { run: deleteConversation } = useRequest(conversationService.deleteConversation, { manual: true })
  const handleDelete = useMemoizedFn(async () => {
    // Add your delete logic here
    Modal.confirm({
      title: 'Delete chat?',
      content: 'Do you want to delete this chat? It cannot be restored after deletion',
      okText: 'Delete',
      onOk: () => {
        deleteConversation(conversation.id)
        refreshConversationList?.()
      }
    })
  })

  const handleRenameSubmit = useMemoizedFn(async () => {
    const values = await form.validate()
    await updateConversationTitle(conversation.id, { title: values.title })
    setRenameVisible(false)
    refreshConversationList?.()
  })

  return (
    <>
      <Trigger
        popup={() => (
          <div className="text-black border border-[#EAEDF1] rounded-[4px] p-[6px] shadow-[0_5px_15px_rgba(0,0,0,0.052)] bg-white">
            <div className="flex items-center mb-[4px] px-[12px] py-[4px]" onClick={() => setRenameVisible(true)}>
              Rename
            </div>
            <div className="flex items-center px-[12px] py-[4px] gap-[6px]" onClick={handleDelete}>
              <IconDelete />
              Delete
            </div>
          </div>
        )}
        alignPoint
        position="bl"
        popupAlign={{
          bottom: 8,
          left: 8
        }}
        trigger="contextMenu">
        <div
          className="cursor-pointer flex items-center gap-[6px]"
          onClick={() => handleGetMessages?.(conversation.id)}>
          <img src={chatHistoryIcon} className="block" />
          <Typography.Title className="!my-0 !flex-1 !text-[13px] !leading-[22px]" ellipsis={{ rows: 1 }}>
            {conversation.title || 'Untitled Conversation'}
          </Typography.Title>
        </div>
      </Trigger>
      <Modal
        okText="Save"
        style={{ width: 480 }}
        title="Rename chat"
        visible={renameVisible}
        onOk={handleRenameSubmit}
        onCancel={() => setRenameVisible(false)}>
        <Form form={form} initialValues={{ title: conversation.title || 'Untitled Conversation' }}>
          <Form.Item field="title" className={'!mb-0'}>
            <Input className={'!w-[432px]'} clearIcon />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
export { ChatHistoryListItem }
