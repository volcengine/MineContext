// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { FC, useMemo, useEffect, useState } from 'react'
import { Form, Button, Select, Input, Typography, Space } from '@arco-design/web-react'
import { find } from 'lodash'

import ModelRadio from './components/modelRadio/model-radio'
import { ModelInfoMap, ModelTypeList, BaseUrl, embeddingModels } from './constants'
import { getModelInfo, updateModelSettings } from '../../services/Settings'
import checkIcon from '../../assets/icons/check.svg'

const FormItem = Form.Item
const { Text } = Typography

interface Props {
  onOk?: () => void
}

const InputBeforeDiv = ({ label }: { label: string }) => {
  return (
    <div className="flex w-[73px] items-center">
      {label}
    </div>
  )
}

const CustomFormItems = () => {
  return (
    <>
    <div className="flex flex-col gap-6 mb-6">
      <div className="flex flex-col gap-[8px]">
        <span className="text-[#0B0B0F] font-roboto text-base font-normal leading-[22px] tracking-[0.042px]">Vision language model</span>
        <FormItem
          field="modelId"
          className="[&_.arco-form-item]: !mb-0"
          rules={[{ required: true, message: 'Cannot be empty' }]}
          requiredSymbol={false}>
          <Input addBefore={<InputBeforeDiv label="Model name" />} placeholder="A VLM model with visual understanding capabilities is required." allowClear className="[&_.arco-input-inner-wrapper]: !w-[574px]" />
        </FormItem>
        <FormItem
          field="baseUrl"
          className="[&_.arco-form-item]: !mb-0"
          rules={[{ required: true, message: 'Cannot be empty' }]}
          requiredSymbol={false}>
          <Input addBefore={<InputBeforeDiv label="Base URL" />} placeholder="Enter your base URL" allowClear className="[&_.arco-input-inner-wrapper]: !w-[574px]" />
        </FormItem>
        <FormItem
          field="apiKey"
          className="[&_.arco-form-item]: !mb-0"
          rules={[{ required: true, message: 'Cannot be empty' }]}
          requiredSymbol={false}>
          <Input addBefore={<InputBeforeDiv label="API Key" />} placeholder="Enter your API Key" allowClear className="[&_.arco-input-inner-wrapper]: !w-[574px]" />
        </FormItem>
      </div>
      <div className="flex flex-col gap-[8px]">
        <span className="text-[#0B0B0F] font-roboto text-base font-normal leading-[22px] tracking-[0.042px]">Embedding model</span>
        <FormItem
          field="embeddingModelId"
          className="[&_.arco-form-item]: !mb-0"
          rules={[{ required: true, message: 'Cannot be empty' }]}
          requiredSymbol={false}>
          <Input addBefore={<InputBeforeDiv label="Model name" />} placeholder="Enter your embedding model name" allowClear className="[&_.arco-input-inner-wrapper]: !w-[574px]" />
        </FormItem>
        <FormItem
          field="embeddingBaseUrl"
          className="[&_.arco-form-item]: !mb-0"
          rules={[{ required: true, message: 'Cannot be empty' }]}
          requiredSymbol={false}>
          <Input addBefore={<InputBeforeDiv label="Base URL" />} placeholder="Enter your base URL" allowClear className="[&_.arco-input-inner-wrapper]: !w-[574px]" />
        </FormItem>
        <FormItem
          field="embeddingApiKey"
          className="[&_.arco-form-item]: !mb-0"
          rules={[{ required: true, message: 'Cannot be empty' }]}
          requiredSymbol={false}>
          <Input addBefore={<InputBeforeDiv label="API Key" />} placeholder="Enter your API Key" allowClear className="[&_.arco-input-inner-wrapper]: !w-[574px]" />
        </FormItem>
        </div>
    </div>
    </>
  )
}

// 1. Add showCheckIcon state
const Settings: FC<Props> = (props: Props) => {
  const { onOk } = props
  const [init, setInit] = useState<undefined | boolean>(undefined)
  const [showCheckIcon, setShowCheckIcon] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const ModelInfoList = ModelInfoMap()
  const [form] = Form.useForm()
  const modelPlatform = Form.useWatch('modelPlatform', form)
  const isCustom = modelPlatform === ModelTypeList.Custom
  const option = useMemo(() => {
    if (isCustom) {
      return []
    }
    form.setFieldValue(
      'modelId',
      modelPlatform === ModelTypeList.Doubao ? 'doubao-seed-1-6-flash-250828' : 'gpt-4.1-nano'
    )
    const foundItem = find(ModelInfoList, (item) => item.value === modelPlatform)

    // If the element is found, return its option, otherwise return an empty array
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
  // 2. Modify the submit function
  const submit = async () => {
    setErrorMessage(null)
    setSuccessMessage(null)

    try {
      const values = await form.validate()

      let param
      if (isCustom) {
        // Custom mode: use form values directly
        param = {
          modelPlatform: values.modelPlatform,
          modelId: values.modelId,
          baseUrl: values.baseUrl,
          apiKey: values.apiKey,
          embeddingModelId: values.embeddingModelId,
          embeddingBaseUrl: values.embeddingBaseUrl,
          embeddingApiKey: values.embeddingApiKey,
          embeddingModelPlatform: values.modelPlatform // Use same platform for embedding in custom mode
        }
      } else {
        // Preset mode (Doubao/OpenAI): use predefined values
        param = {
          modelPlatform: values.modelPlatform,
          modelId: values.modelId,
          baseUrl: values.modelPlatform === ModelTypeList.Doubao ? BaseUrl.DoubaoUrl : BaseUrl.OpenAIUrl,
          apiKey: values.apiKey,
          embeddingModelId:
            values.modelPlatform === ModelTypeList.Doubao
              ? embeddingModels.DoubaoEmbeddingModelId
              : embeddingModels.OpenAIEmbeddingModelId
        }
      }

      await updateModelSettings(param)

      // Use state instead of Message.success to avoid React 19 compatibility issues
      setSuccessMessage('Your API key saved successfully')

      // 显示检查图标
      setShowCheckIcon(true)

      // 3秒后隐藏检查图标和成功消息
      setTimeout(() => {
        setShowCheckIcon(false)
        setSuccessMessage(null)
      }, 3000)

      if (!init) {
        onOk?.()
      }
    } catch (error: any) {
      // Handle backend errors - use state instead of Message.error
      const errMsg = error?.response?.data?.message || error?.message || 'Failed to save settings'
      console.error('Failed to update model settings:', error)
      setErrorMessage(errMsg)

      // Auto-hide error after 5 seconds
      setTimeout(() => {
        setErrorMessage(null)
      }, 5000)
    }
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
            {isCustom ? (
              <CustomFormItems />
            ) : (
              <>
                <FormItem
                  label="Select AI model"
                  field={'modelId'}
                  requiredSymbol={false}
                  // initialValue={'doubao-seed-1-6-250615'}
                  rules={[{ required: true, message: 'Please select' }]}>
                  <Select
                    allowCreate
                    placeholder="please select"
                    options={option}
                    className="[&_.arco-select]: !w-[574px]"
                  />
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
                  <Input autoFocus placeholder="Enter your API key" allowClear className="[&_.arco-input-inner-wrapper]: !w-[574px]" />
                </FormItem>
              </>
            )}

            {/* Success and Error Messages */}
            {successMessage && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md text-green-800 text-sm">
                {successMessage}
              </div>
            )}
            {errorMessage && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-800 text-sm">
                {errorMessage}
              </div>
            )}

            <FormItem>
              <Space>
                {/* Determine if it is a routing page or a guide */}
                {!init ? (
                  <Button
                    type="primary"
                    htmlType="submit"
                    onClick={submit}
                    className="[&_.arco-btn-primary]: !bg-[#000]">
                    Get started
                  </Button>
                ) : (
                  <div className="flex items-center gap-[8px]">
                    <Button
                      type="primary"
                      className="[&_.arco-btn-primary]: !bg-[#000]"
                      htmlType="submit"
                      onClick={submit}>
                      Save
                    </Button>
                    {showCheckIcon && <img src={checkIcon} alt="check" className="w-[20px] h-[20px] mr-[8px]" />}
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
