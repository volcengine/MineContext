import React from 'react'
import { Button, Modal, Slider, TimePicker, Radio, Form, Checkbox, Spin, Switch } from '@arco-design/web-react'
import clsx from 'clsx'
import { Application } from './application'
import screenIcon from '@renderer/assets/icons/screen.svg'
interface SettingsModalProps {
  visible: boolean
  form: any
  sources: any
  screenAllSources: any[]
  appAllSources: any[]
  applicationVisible: boolean
  tempRecordInterval: number
  tempEnableRecordingHours: boolean
  tempRecordingHours: [string, string]
  tempApplyToDays: string
  onCancel: () => void
  onSave: () => void
  onSetApplicationVisible: (visible: boolean) => void
  onSetTempRecordInterval: (value: number) => void
  onSetTempEnableRecordingHours: (value: boolean) => void
  onSetTempRecordingHours: (value: [string, string]) => void
  onSetTempApplyToDays: (value: string) => void
}

const SettingsModal: React.FC<SettingsModalProps> = ({
  visible,
  form,
  sources,
  screenAllSources,
  appAllSources,
  applicationVisible,
  tempRecordInterval,
  tempEnableRecordingHours,
  tempRecordingHours,
  tempApplyToDays,
  onCancel,
  onSave,
  onSetApplicationVisible,
  onSetTempRecordInterval,
  onSetTempEnableRecordingHours,
  onSetTempRecordingHours,
  onSetTempApplyToDays
}) => {
  return (
    <Modal
      title="Settings"
      visible={visible}
      autoFocus={false}
      focusLock
      onCancel={onCancel}
      className="text-[#AEAFC2]"
      unmountOnExit
      footer={
        <>
          <Button onClick={onCancel} className="[&_.arco-btn]: !text-xs">
            Cancel
          </Button>
          <Button type="primary" onClick={onSave} className="[&_.arco-btn-primary]: !bg-black">
            Save
          </Button>
        </>
      }>
      <Form layout="vertical" form={form}>
        <div className="flex w-full flex-1 mt-5">
          <div className="flex flex-col flex-1 pr-[24px]">
            <Form.Item label="Record Interval" className="[&_.arco-form-item-label]:!text-xs">
              <Slider
                value={tempRecordInterval}
                onChange={(value) => onSetTempRecordInterval(value as number)}
                min={5}
                max={300}
                marks={{
                  5: '5s',
                  300: '5min'
                }}
                className="!mt-4"
                formatTooltip={(value) => `${value}s`}
              />
            </Form.Item>
            <Form.Item label="Choose what to record" shouldUpdate>
              {(values) => {
                const { screenSources = [], windowSources = [] } = values || {}
                const screenList = screenAllSources?.filter((source) => screenSources.includes(source.id)) || []
                const windowList = appAllSources?.filter((source) => windowSources.includes(source.id)) || []
                return (
                  <Spin loading={sources.state === 'loading'} block>
                    <Application
                      value={[...screenList, ...windowList]}
                      onCancel={() => onSetApplicationVisible(false)}
                      visible={applicationVisible}
                      onOk={() => onSetApplicationVisible(true)}
                    />
                  </Spin>
                )
              }}
            </Form.Item>
            <Form.Item label="Enable recording hours" className="[&_.arco-form-item-label]:!text-xs !mb-0">
              <Switch
                checked={tempEnableRecordingHours}
                onChange={onSetTempEnableRecordingHours}
                className={
                  !tempEnableRecordingHours ? '[&_.arco-switch]: !bg-[#e2e3ef]' : '[&_.arco-switch]: !bg-black'
                }
              />
            </Form.Item>
            {tempEnableRecordingHours && (
              <div className="!mt-3">
                <Form.Item label="Set recording hours" className="[&_.arco-form-item-label]:!text-xs">
                  <TimePicker.RangePicker
                    format="HH:mm"
                    value={tempRecordingHours}
                    onChange={(value) => onSetTempRecordingHours(value as [string, string])}
                  />
                </Form.Item>
                <Form.Item label="Apply to days" className="[&_.arco-form-item-label]: !text-xs">
                  <Radio.Group value={tempApplyToDays} onChange={onSetTempApplyToDays}>
                    <Radio value="weekday" className="[&_.arco-radio-mask]: !border-[#d7daea]">
                      Only weekday
                    </Radio>
                    <Radio value="everyday" className="[&_.arco-radio-mask]: !border-[#d7daea]">
                      Everyday
                    </Radio>
                  </Radio.Group>
                </Form.Item>
              </div>
            )}
          </div>
          <div
            className={clsx(
              'flex flex-col flex-1 border-l border-[#efeff4] max-h-[360px] h-[360px] overflow-x-hidden overflow-y-auto px-[16px]  [&_.arco-checkbox-checked_.arco-checkbox-mask]:!bg-[#000000] [&_.arco-checkbox-checked_.arco-checkbox-mask]:!border-[#000000]',
              { hidden: !applicationVisible }
            )}>
            <div className="text-[15px] leading-[18px] text-[#42464e] mb-[12px] font-medium">Choose what to record</div>
            <div className="[&_.arco-checkbox]:!flex [&_.arco-checkbox]:!items-center">
              <div className="text-[14px] leading-[20px] text-[#42464e] mb-[4px]">Screen</div>
              <Form.Item field="screenSources">
                <Checkbox.Group>
                  {screenAllSources.map((source) => (
                    <Checkbox key={source.id} value={source.id}>
                      <div className="flex items-center space-x-[4px]">
                        {source.appIcon ? (
                          <img
                            src={source.appIcon || ''}
                            alt=""
                            className="w-[14px] h-[14px] inline-block object-cover"
                          />
                        ) : (
                          <img src={screenIcon} alt="" className="w-[14px] h-[14px] inline-block object-cover" />
                        )}
                        <div className="text-[13px] leading-[22px] text-[#0b0b0f] !ml-[4px] line-clamp-1">
                          {source.name}
                        </div>
                      </div>
                    </Checkbox>
                  ))}
                </Checkbox.Group>
              </Form.Item>
            </div>
            <div className="[&_.arco-checkbox]:!flex [&_.arco-checkbox]:!items-center">
              <div className="text-[14px] leading-[20px] text-[#42464e] mb-[4px]">Window</div>
              <div className="text-[10px] leading-[12px] text-[#737a87] mb-[4px]">
                Only opened applications can be selected
              </div>
              <Form.Item field="windowSources">
                <Checkbox.Group className="flex flex-col space-y-4">
                  {appAllSources.map((source) => (
                    <Checkbox key={source.id} value={source.id}>
                      <div className="flex items-center space-x-[4px]">
                        <img
                          src={source.appIcon || source.thumbnail || ''}
                          alt=""
                          className="w-[14px] h-[14px] inline-block object-cover"
                        />
                        <div className="text-[13px] leading-[22px] text-[#0b0b0f] !ml-[4px] line-clamp-1">
                          {source.name}
                        </div>
                      </div>
                    </Checkbox>
                  ))}
                </Checkbox.Group>
              </Form.Item>
            </div>
          </div>
        </div>
      </Form>
    </Modal>
  )
}

export default SettingsModal
