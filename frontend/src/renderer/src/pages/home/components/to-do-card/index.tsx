// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import {
  Button,
  Card,
  Input,
  Message,
  Modal,
  Popconfirm,
  Radio,
  Select,
  Space,
  Typography,
  Tree,
  Form
} from '@arco-design/web-react'
import { IconDelete, IconEdit } from '@arco-design/web-react/icon'
import { Task, useHomeInfo } from '@renderer/hooks/useHomeInfo'
import { useRef, useState } from 'react'
import taskEmpty from '@renderer/assets/images/task-empty.svg'
import addIcon from '@renderer/assets/icons/add.svg'
import { useInitPrepareData } from '@renderer/hooks/use-init-prepera-data'
import { TaskUrgency, TODO_LIST_STATUS } from '@renderer/constant/feed'
import { useMemoizedFn } from 'ahooks'
import highPriorityIcon from '@renderer/assets/icons/high-priority.svg'
import mediumPriorityIcon from '@renderer/assets/icons/medium-priority.svg'
import lowPriorityIcon from '@renderer/assets/icons/low-priority.svg'
import doneIcon from '@renderer/assets/icons/done.svg'

const { Text } = Typography
const TextArea = Input.TextArea
const TreeNode = Tree.Node

function getTodoIcon(urgency: TaskUrgency) {
  switch (urgency) {
    case TaskUrgency.High:
      return highPriorityIcon
    case TaskUrgency.Medium:
      return mediumPriorityIcon
    case TaskUrgency.Low:
      return lowPriorityIcon
    case TaskUrgency.Done:
      return doneIcon
    default:
      return lowPriorityIcon
  }
}

function genTodoTitle(urgency: TaskUrgency) {
  switch (urgency) {
    case TaskUrgency.High:
      return 'Urgent'
    case TaskUrgency.Medium:
      return 'Medium Priority'
    case TaskUrgency.Low:
      return 'Low Priority'
    case TaskUrgency.Done:
      return 'Done'
    default:
      return 'Unknown Priority'
  }
}

const ToDoCard: React.FC = () => {
  const { tasks, toggleTaskStatus, updateTask, deleteTask, addTask } = useHomeInfo()
  const hasTasks = tasks.length > 0
  const [isTaskHover, setIsTaskHover] = useState<number | null>(null) // Edit task status
  const [isDeleting, setIsDeleting] = useState(false)
  const { deleteTodoList, data: todoListInitData } = useInitPrepareData()
  const [form] = Form.useForm()
  const filterDoneTasks = tasks.map((task) => {
    // After a task is done, its urgency becomes -1
    if (task.status === 1) {
      return {
        ...task,
        urgency: TaskUrgency.Done
      }
    }
    return task
  })

  // Handle deleting a task
  const handleDeleteTask = useMemoizedFn(async (taskId: number) => {
    try {
      await deleteTask(taskId)
      // TODO: Separate deletion from initial data
      deleteTodoList(taskId)
      Message.success('task delete success')
    } catch (error) {
      Message.error('task delete failed')
    } finally {
      setIsDeleting(false)
      setIsTaskHover(null)
    }
  })

  const renderTask = (task) => (
    <div
      key={task.id}
      className="flex w-full px-6 max-w-[1000px] items-center justify-between rounded-[4px]"
      onMouseEnter={() => {
        setIsTaskHover(task.id)
      }}
      onMouseLeave={() => {
        if (!isDeleting) {
          setIsTaskHover(null)
        }
      }}>
      <div className="gap-2 flex-1 flex items-center">
        <Radio checked={!!task.status} onClick={() => handleToggleTaskStatus(task)} />
        <div
          className={`font-roboto text-sm font-normal text-[#3F3F51] leading-[22px] max-w-[800px] tracking-[0.042px] whitespace-normal break-words ${task.status && 'line-through'}`}>
          {task.content}
        </div>
      </div>
      <div className={`flex items-center gap-2 ${isTaskHover === task.id ? 'opacity-100' : 'opacity-0'}`}>
        <Button
          type="text"
          size="small"
          icon={<IconEdit />}
          onClick={() => handleEditToDoList(task)}
          style={{ color: '#165dff' }}
          disabled={!!task.status}
        />
        <Popconfirm
          title="Confirm delete"
          content="Confirm to delete this task?"
          onOk={() => handleDeleteTask(task.id)}
          onCancel={() => {
            setIsDeleting(false)
            setIsTaskHover(null)
          }}
          onVisibleChange={(visible) => {
            if (!visible) {
              setIsDeleting(false)
              setIsTaskHover(null)
            }
          }}
          okText="Confirm"
          cancelText="Cancel">
          <Button
            type="text"
            size="small"
            icon={<IconDelete />}
            style={{ color: '#f53f3f' }}
            onClick={() => {
              setIsDeleting(true)
            }}
          />
        </Popconfirm>
      </div>
    </div>
  )

  function buildTodoTree(tasks: Task[]) {
    const rootTitle = (urgency: TaskUrgency) => (
      <div className="flex items-center gap-2">
        <img src={getTodoIcon(urgency)} alt="todoIcon" />
        <div
          className="font-roboto text-sm text-[#0B0B0F] leading-[22px] tracking-[0.042px]"
          style={{
            fontWeight: 500
          }}>
          {genTodoTitle(urgency)}
        </div>
      </div>
    )

    const baseTree: { title: React.ReactNode; key: string; children: { title: React.ReactNode; key: string }[] }[] = [
      {
        title: rootTitle(TaskUrgency.High),
        key: genTodoTitle(TaskUrgency.High),
        children: []
      },
      {
        title: rootTitle(TaskUrgency.Medium),
        key: genTodoTitle(TaskUrgency.Medium),
        children: []
      },
      {
        title: rootTitle(TaskUrgency.Low),
        key: genTodoTitle(TaskUrgency.Low),
        children: []
      },
      {
        title: rootTitle(TaskUrgency.Done),
        key: genTodoTitle(TaskUrgency.Done),
        children: []
      }
    ]
    tasks.forEach((task) => {
      const taskTitle = renderTask(task)
      const nodeParam = {
        title: taskTitle,
        key: String(task.id)
      }
      switch (task.urgency) {
        case TaskUrgency.High:
          baseTree[0].children.push(nodeParam)
          break
        case TaskUrgency.Medium:
          baseTree[1].children.push(nodeParam)
          break
        case TaskUrgency.Low:
          baseTree[2].children.push(nodeParam)
          break
        case TaskUrgency.Done:
          baseTree[3].children.push(nodeParam)
          break
      }
    })
    const retTree = baseTree.filter((node) => node.children.length > 0)
    return (
      <Tree autoExpandParent blockNode actionOnClick="expand">
        {retTree.map((node) => (
          <TreeNode key={node.key} title={node.title}>
            {node.children.map((child) => (
              <TreeNode
                key={child.key}
                title={child.title}
                className="[&_.arco-tree-node-indent]:hidden [&_.arco-tree-node-switcher]:hidden"
              />
            ))}
          </TreeNode>
        ))}
      </Tree>
    )
  }

  const [status, setStatus] = useState(TODO_LIST_STATUS.Create)
  const [visible, setVisible] = useState(false)
  const handleCreateToDoList = useMemoizedFn(() => {
    setStatus(TODO_LIST_STATUS.Create)
    setVisible(true)
  })
  const timer = useRef<NodeJS.Timeout>(null)
  const handleToggleTaskStatus = useMemoizedFn(async (task) => {
    let id = task.id
    console.log('id --->', id)
    if (todoListInitData.some((v) => v.id === task.id)) {
      deleteTodoList(task.id)
      id = await addTask({
        content: task.content,
        urgency: task.urgency,
        status: 0
      })
      console.log('id --->', id)
    }
    timer.current = setTimeout(() => {
      toggleTaskStatus(id)
    }, 300)
  })
  const handleEditToDoList = useMemoizedFn((task) => {
    setStatus(TODO_LIST_STATUS.Edit)
    setVisible(true)
    timer.current = setTimeout(() => {
      form.setFieldsValue(task)
    }, 100)
  })
  const createTodoList = useMemoizedFn(async () => {
    try {
      await form.validate()
      const values = form.getFieldsValue()
      await addTask({
        content: values.content,
        urgency: values.urgency
      })
      Message.success('Task add success')
    } catch (error: any) {
      Message.error(error.message || '')
    }
  })

  const editTodoList = useMemoizedFn(async () => {
    try {
      await form.validate()
      const values = form.getFieldsValue()
      if (todoListInitData.some((v) => v.id === values.id)) {
        deleteTodoList(values.id)
        await addTask({
          content: values.content,
          urgency: values.urgency
        })
      } else {
        await updateTask(values.id, {
          content: values.content,
          urgency: values.urgency
        })
      }
      Message.success('task update success')
    } catch (error: any) {
      Message.error(error.message || '')
    }
  })

  const handleSave = useMemoizedFn(async () => {
    try {
      if (status === TODO_LIST_STATUS.Create) {
        await createTodoList()
      } else {
        await editTodoList()
      }
      setVisible(false)
    } catch (e: any) {
      Message.error(e.message || '')
    } finally {
      clearTimeout(timer.current!)
    }
  })

  return (
    <>
      <Card
        className="flex max-h-[460px] p-3 flex-col items-start gap-4 self-stretch rounded-[10px] border border-[var(--line-color-border-3,#E1E3EF)] bg-white w-full"
        headerStyle={{
          width: '100%'
        }}
        title={
          <div className="flex flex-1 justify-between items-center w-full">
            <Space style={{ marginTop: 5 }}>
              <div className="flex px-[2px] justify-center items-center gap-[4px] rounded-[2px] bg-gradient-to-l from-[rgba(239,251,248,0.5)] to-[#F5FBEF]">
                <div className="mr-[0.3em] font-['Byte Sans'] text-[15px] font-extralight leading-[22px] tracking-[0.045px] bg-gradient-to-l from-[#007740] to-[#D0B400] bg-clip-text text-transparent">
                  Todo
                </div>
              </div>
              <div className="text-black font-['Roboto'] text-sm font-medium leading-[22px] tracking-[0.042px]">
                today
              </div>
            </Space>
            <img src={addIcon} alt="" onClick={handleCreateToDoList} className="cursor-pointer" />
          </div>
        }
        bodyStyle={{
          alignItems: hasTasks ? 'flex-start' : 'center',
          justifyContent: hasTasks ? 'flex-start' : 'center',
          width: '100%',
          overflow: 'auto',
          scrollbarWidth: 'none',
          marginTop: '-10px'
        }}>
        <div className={`flex h-[340px] max-h-[340px] flex-col gap-4 self-stretch`}>
          {hasTasks ? (
            <div>{buildTodoTree([...(todoListInitData as any), ...filterDoneTasks])}</div>
          ) : (
            <div className="empty-state">
              <img src={taskEmpty} alt="empty" />
              <Text type="secondary">Update at 8 am everyday</Text>
            </div>
          )}
        </div>
      </Card>
      {/* Edit task modal */}
      <Modal
        title={status === TODO_LIST_STATUS.Create ? 'Add todo' : 'Edit todo task'}
        visible={visible}
        onOk={handleSave}
        onCancel={() => setVisible(false)}
        okText={status === TODO_LIST_STATUS.Create ? 'Add' : 'Update'}
        cancelText="Cancel"
        unmountOnExit>
        <Form
          layout="vertical"
          form={form}
          initialValues={{ urgency: TaskUrgency.Low }}
          className="[&_.arco-form-label-item>label]:!flex">
          <Form.Item field="id" noStyle>
            <Input className="hidden" />
          </Form.Item>
          <Form.Item
            label="Todo content"
            field="content"
            rules={[{ required: true, message: 'Please input task content' }]}>
            <TextArea autoSize placeholder="Input todo content" />
          </Form.Item>
          <Form.Item label="Priority" field="urgency">
            <Select>
              <Select.Option value={TaskUrgency.High}>Urgent</Select.Option>
              <Select.Option value={TaskUrgency.Medium}>Medium Priority</Select.Option>
              <Select.Option value={TaskUrgency.Low}>Low Priority</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
export { ToDoCard }
