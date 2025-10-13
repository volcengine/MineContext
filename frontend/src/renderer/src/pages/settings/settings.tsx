// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { FC, useMemo, useEffect, useState } from 'react'
import { Form, Button, Select, Input, Typography, Space, Message } from '@arco-design/web-react'
import ModelRadio from './components/modelRadio/ModelRadio'
const FormItem = Form.Item
import { ModelInfoMap, ModelTypeList, BaseUrl, embeddingModels } from './constants'
const { Text } = Typography
import { find } from 'lodash'
import checkIcon from '../../assets/icons/check.svg'

import { getModelInfo, updateModelSettings } from '../../services/Settings'

interface Props {
  onOk?: () => void
}

// 1. 添加 showCheckIcon 状态
const Settings: FC<Props> = (props: Props) => {
  const { onOk } = props
  const [init, setInit] = useState<undefined | boolean>(undefined)
  const [showCheckIcon, setShowCheckIcon] = useState(false)

  const ModelInfoList = ModelInfoMap()
  const [form] = Form.useForm()
  const modelPlatform = Form.useWatch('modelPlatform', form)
  const option = useMemo(() => {
    form.setFieldValue(
      'modelId',
      modelPlatform === ModelTypeList.Doubao ? 'doubao-seed-1-6-flash-250828' : 'gpt-4.1-nano'
    )
    const foundItem = find(ModelInfoList, (item) => item.value === modelPlatform)

    // 如果找到元素则返回其option，否则返回空数组
    return foundItem ? foundItem.option : []
  }, [modelPlatform])

  const getInfo = async () => {
    const res = await getModelInfo()

    if (res.data.config.apiKey === '') {
      setInit(false)
    } else {
      form.setFieldsValue(res.data.config)
      setInit(true)
    }
  }
  useEffect(() => {
    getInfo()
  }, [])
  // 2. 修改 submit 函数
  const submit = async () => {
    const values = await form.validate()
    const param = {
      ...values,
      baseUrl: values.modelPlatform === ModelTypeList.Doubao ? BaseUrl.DoubaoUrl : BaseUrl.OpenAIUrl,
      embeddingModelId:
        values.modelPlatform === ModelTypeList.Doubao
          ? embeddingModels.DoubaoEmbeddingModelId
          : embeddingModels.OpenAIEmbeddingModelId
    }
    // const res = await updateModelSettings(param)
    await updateModelSettings(param)
    Message.success('Your API key saved successfully')

    // 显示检查图标
    setShowCheckIcon(true)

    // 3秒后隐藏检查图标
    setTimeout(() => {
      setShowCheckIcon(false)
    }, 3000)

    if(!init) {
      onOk?.()
    }
    // if (res.data.success) {
    //   Message.success('Your API Key saved successfully')
    //   if (!init) {
    //     onOk?.()
    //   }
    // } else {
    //   Message.error('error')
    // }
  }

  return (
    <div className="fixed top-0 left-0 flex flex-col h-full overflow-y-hidden p-[8px] pl-0 rounded-[20px] relative ">
      <div className="bg-white rounded-[16px] pl-6 h-[calc(100%-8px)] flex flex-col h-full overflow-y-auto overflow-x-hidden scrollbar-hide pb-2">
        <div className="mb-[12px]">
          <div className="mt-[26px] mb-[10px] text-[24px] font-bold text-[#000]">{'Select a AI model to start'}</div>
          <Text type="secondary" className="text-[13px]">
            {'Configure AI model and API Key, then you can start MineContext’s intelligent context capability'}
          </Text>
        </div>

        <div>
          <Form autoComplete="off" layout={'vertical'} form={form}>
            <FormItem
              label="Model platform"
              field={'modelPlatform'}
              requiredSymbol={false}
              initialValue={ModelTypeList.Doubao}
              rules={[{ required: true, message: 'Please select' }]}>
              <ModelRadio />
            </FormItem>
            <FormItem
              label="Select AI model"
              field={'modelId'}
              requiredSymbol={false}
              // initialValue={'doubao-seed-1-6-250615'}
              rules={[{ required: true, message: 'Please select' }]}>
              <Select allowCreate placeholder="please select" options={option} style={{ width: '574px' }} />
            </FormItem>
            <FormItem
              requiredSymbol={false}
              label="API Key"
              field={'apiKey'}
              extra={
                <div className="flex items-center text-[#6E718C] text-[14px] ">
                  You can get the API Key Here:{' '}
                  <Button
                    onClick={() => {
                      const url =
                        modelPlatform === ModelTypeList.Doubao
                          ? 'https://www.volcengine.com/docs/82379/1541594'
                          : 'https://platform.openai.com/settings/organization/api-keys'
                      window.open(`${url}`)
                    }}
                    type="text">
                    {modelPlatform === ModelTypeList.Doubao ? 'Get Doubao API Key' : 'Get OpenAI API Key'}
                  </Button>
                </div>
              }
              rules={[{ required: true, message: 'Please enter' }]}>
              <Input autoFocus placeholder="Enter your API key" allowClear style={{ width: '574px' }} />
            </FormItem>

            <FormItem>
              <Space>
                {/* 判断时路由页面还是引导 */}
                {!init ? (
                  <Button type="primary" htmlType="submit" onClick={submit} style={{ background: '#000' }}>
                    Get started
                  </Button>
                ) : (
                  <div className="flex items-center gap-[8px]">
                    <Button type="primary" style={{ background: '#000' }} htmlType="submit" onClick={submit}>
                      Save
                    </Button>
                    {showCheckIcon && (
                      <img src={checkIcon} alt="check" className="w-[20px] h-[20px] mr-[8px]" />
                    )}
                  </div>

                )}
              </Space>
            </FormItem>
          </Form>
        </div>
      </div>
    </div>
  )
}

export default Settings
