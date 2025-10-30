// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { FC, useMemo, useEffect } from 'react'
import { Form, Button, Select, Input, Typography, Spin, Message } from '@arco-design/web-react'
import { find, get, isEmpty, pick } from 'lodash'

import ModelRadio from './components/modelRadio/model-radio'
import { ModelTypeList, BaseUrl, embeddingModels, ModelInfoList } from './constants'
import { getModelInfo, ModelConfigProps, updateModelSettingsAPI } from '../../services/Settings'
import { useMemoizedFn, useMount, useRequest } from 'ahooks'

const FormItem = Form.Item
const { Text } = Typography

interface SettingsProps {
  closeSetting?: () => void
  init?: boolean
}
export interface InputPrefixProps {
  label: string
}
const InputPrefix: FC<InputPrefixProps> = (props) => {
  const { label } = props
  return <div className="flex w-[73px] items-center">{label}</div>
}
export interface CustomFormItemsProps {
  prefix: string
}
const CustomFormItems: FC<CustomFormItemsProps> = (props) => {
  const { prefix } = props
  return (
    <>
      <div className="flex flex-col gap-6 mb-6">
        <div className="flex flex-col gap-[8px]">
          <span className="text-[#0B0B0F] font-roboto text-base font-normal leading-[22px] ">
            Vision language model
          </span>
          <FormItem
            field={`${prefix}-modelId`}
            className="!mb-0"
            rules={[{ required: true, message: 'Cannot be empty' }]}
            requiredSymbol={false}>
            <Input
              addBefore={<InputPrefix label="Model name" />}
              placeholder="A VLM model with visual understanding capabilities is required."
              allowClear
              className="[&_.arco-input-inner-wrapper]: !w-[574px]"
            />
          </FormItem>
          <FormItem
            field={`${prefix}-baseUrl`}
            className="!mb-0"
            rules={[{ required: true, message: 'Cannot be empty' }]}
            requiredSymbol={false}>
            <Input
              addBefore={<InputPrefix label="Base URL" />}
              placeholder="Enter your base URL"
              allowClear
              className="[&_.arco-input-inner-wrapper]: !w-[574px]"
            />
          </FormItem>
          <FormItem
            field={`${prefix}-apiKey`}
            className="!mb-0"
            rules={[{ required: true, message: 'Cannot be empty' }]}
            requiredSymbol={false}>
            <Input
              addBefore={<InputPrefix label="API Key" />}
              placeholder="Enter your API Key"
              allowClear
              className="!w-[574px]"
            />
          </FormItem>
        </div>
        <div className="flex flex-col gap-[8px]">
          <span className="text-[#0B0B0F] font-roboto text-base font-normal leading-[22px]">Embedding model</span>
          <FormItem
            field={`${prefix}-embeddingModelId`}
            className="!mb-0"
            rules={[{ required: true, message: 'Cannot be empty' }]}
            requiredSymbol={false}>
            <Input
              addBefore={<InputPrefix label="Model name" />}
              placeholder="Enter your embedding model name"
              allowClear
              className="!w-[574px]"
            />
          </FormItem>
          <FormItem
            field={`${prefix}-embeddingBaseUrl`}
            className="!mb-0"
            rules={[{ required: true, message: 'Cannot be empty' }]}
            requiredSymbol={false}>
            <Input
              addBefore={<InputPrefix label="Base URL" />}
              placeholder="Enter your base URL"
              allowClear
              className="!w-[574px]"
            />
          </FormItem>
          <FormItem
            field={`${prefix}-embeddingApiKey`}
            className="!mb-0"
            rules={[{ required: true, message: 'Cannot be empty' }]}
            requiredSymbol={false}>
            <Input
              addBefore={<InputPrefix label="API Key" />}
              placeholder="Enter your API Key"
              allowClear
              className="!w-[574px]"
            />
          </FormItem>
        </div>
      </div>
    </>
  )
}
export interface StandardFormItemsProps {
  modelPlatform: ModelTypeList
  prefix: string
}
const StandardFormItems: FC<StandardFormItemsProps> = (props) => {
  const { modelPlatform, prefix } = props
  const option = useMemo(() => {
    const foundItem = find(ModelInfoList, (item) => item.value === modelPlatform)
    return foundItem ? foundItem.option : []
  }, [modelPlatform])

  return (
    <>
      <FormItem
        label="Select AI model"
        field={`${prefix}-modelId`}
        requiredSymbol={false}
        rules={[
          {
            validator(value, callback) {
              if (!value) {
                callback('Please select AI model')
              } else {
                callback()
              }
            }
          }
        ]}>
        <Select allowCreate placeholder="please select" options={option} className="!w-[574px]" />
      </FormItem>
      <FormItem
        requiredSymbol={false}
        label="API Key"
        field={`${prefix}-apiKey`}
        extra={
          <div className="flex items-center text-[#6E718C] text-[14px] ">
            You can get the API Key Here:
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
        rules={[
          {
            validator(value, callback) {
              if (!value) {
                callback('Please enter your API key')
              } else {
                callback()
              }
            }
          }
        ]}>
        <Input autoFocus placeholder="Enter your API key" allowClear className="!w-[574px]" />
      </FormItem>
    </>
  )
}

// 1. Add showCheckIcon state
export interface SettingsFormBase {
  modelPlatform: string
}

export type SettingsFormProps = SettingsFormBase & {
  [K in ModelTypeList as `${K}-modelId` | `${K}-apiKey`]?: string
} & {
  [K in
    | `${ModelTypeList.Custom}-embeddingModelId`
    | `${ModelTypeList.Custom}-embeddingBaseUrl`
    | `${ModelTypeList.Custom}-embeddingApiKey`]?: string
}
const Settings: FC<SettingsProps> = (props) => {
  const { closeSetting, init } = props

  const [form] = Form.useForm<SettingsFormProps>()
  const { run: getInfo, loading: getInfoLoading, data: modelInfo } = useRequest(getModelInfo, { manual: true })

  const { run: updateModelSettings, loading: updateLoading } = useRequest(updateModelSettingsAPI, {
    manual: true,
    onSuccess() {
      Message.success('Your API key saved successfully')
      getInfo()
      if (init) {
        closeSetting?.()
      }
    },
    onError(e: Error) {
      const errMsg = get(e, 'response.data.message') || get(e, 'message') || 'Failed to save settings'
      Message.error(errMsg)
    }
  })
  const submit = useMemoizedFn(async () => {
    try {
      await form.validate()
      const values = form.getFieldsValue()
      const isCustom = values.modelPlatform === ModelTypeList.Custom
      if (!values.modelPlatform) {
        Message.error('Please select Model Platform')
        return
      }
      const commonKey = [
        'modelPlatform',
        `${values.modelPlatform}-modelId`,
        `${values.modelPlatform}-apiKey`,
        `${values.modelPlatform}-baseUrl`,
        `${values.modelPlatform}-embeddingModelId`,
        `${values.modelPlatform}-embeddingBaseUrl`,
        `${values.modelPlatform}-embeddingApiKey`
      ]
      const data = pick(values, commonKey)
      const formatData = Object.fromEntries(
        Object.entries(data).map(([key, value]) => [key.replace(`${values.modelPlatform}-`, ''), value])
      )
      const params = isCustom
        ? formatData
        : {
            ...formatData,
            baseUrl: values.modelPlatform === ModelTypeList.Doubao ? BaseUrl.DoubaoUrl : BaseUrl.OpenAIUrl,
            embeddingModelId:
              values.modelPlatform === ModelTypeList.Doubao
                ? embeddingModels.DoubaoEmbeddingModelId
                : embeddingModels.OpenAIEmbeddingModelId
          }

      updateModelSettings(params as unknown as ModelConfigProps)
    } catch (error: any) {}
  })

  useMount(() => {
    getInfo()
  })
  useEffect(() => {
    const config = get(modelInfo, 'config')
    if (!getInfoLoading && !isEmpty(config) && !init) {
      const settingsValue = new Map<keyof SettingsFormProps, string>()
      const prefix = config.modelPlatform as ModelTypeList
      settingsValue.set(`modelPlatform`, prefix)
      Object.keys(config).reduce((acc, key) => {
        if (!acc.has(`${prefix}-${key}` as keyof SettingsFormProps) && !!config[key]) {
          acc.set(`${prefix}-${key}` as keyof SettingsFormProps, config[key])
        }
        return acc
      }, settingsValue)
      form.setFieldsValue(Object.fromEntries(settingsValue))
    }
  }, [modelInfo, getInfoLoading])

  return (
    <Spin loading={getInfoLoading} block className="[&_.arco-spin-children]:!h-full !h-full">
      <div className="top-0 left-0 flex flex-col h-full overflow-y-hidden p-2 relative">
        <div className="bg-white rounded-[16px] pl-6 flex flex-col h-full overflow-y-auto overflow-x-hidden scrollbar-hide pb-2">
          <div className="mb-[12px]">
            <div className="mt-[26px] mb-[10px] text-[24px] font-bold text-[#000]">Select a AI model to start</div>
            <Text type="secondary" className="text-[13px]">
              Configure AI model and API Key, then you can start MineContext’s intelligent context capability
            </Text>
          </div>

          <div>
            <Form
              autoComplete="off"
              layout={'vertical'}
              form={form}
              initialValues={{
                modelPlatform: ModelTypeList.Doubao,
                [`${ModelTypeList.Doubao}-modelId`]: 'doubao-seed-1-6-flash-250828',
                [`${ModelTypeList.OpenAI}-modelId`]: 'gpt-4.1-nano'
              }}>
              <FormItem label="Model platform" field={'modelPlatform'} requiredSymbol={false}>
                <ModelRadio />
              </FormItem>
              <FormItem
                shouldUpdate={(prevValues, currentValues) => prevValues.modelPlatform !== currentValues.modelPlatform}
                noStyle>
                {(values) => {
                  const modelPlatform = values.modelPlatform
                  if (modelPlatform === ModelTypeList.Custom) {
                    return <CustomFormItems prefix={ModelTypeList.Custom} />
                  } else if (modelPlatform === ModelTypeList.Doubao) {
                    return <StandardFormItems modelPlatform={modelPlatform} prefix={ModelTypeList.Doubao} />
                  } else if (modelPlatform === ModelTypeList.OpenAI) {
                    return <StandardFormItems modelPlatform={modelPlatform} prefix={ModelTypeList.OpenAI} />
                  } else {
                    return null
                  }
                }}
              </FormItem>
            </Form>
            <Spin loading={updateLoading}>
              <Button type="primary" onClick={submit} disabled={updateLoading} className="!bg-[#000]">
                {init ? 'Get started' : 'Save'}
              </Button>
            </Spin>
          </div>
        </div>
      </div>
    </Spin>
  )
}

export default Settings
