import { Divider, Message, Spin, Trigger } from '@arco-design/web-react'
import { IconDown, IconLeft, IconRight } from '@arco-design/web-react/icon'
import { Heatmap, DayCellProps } from '@zhongyao/heatmap'
import { useMemoizedFn, useRequest } from 'ahooks'
import dayjs from 'dayjs'
import { capitalize, get, set } from 'lodash'
import { FC, useEffect, useMemo, useState } from 'react'
import advancedFormat from 'dayjs/plugin/advancedFormat'
import clsx from 'clsx'
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter'
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore'

dayjs.extend(isSameOrAfter)
dayjs.extend(isSameOrBefore)
dayjs.extend(advancedFormat)
const getColor = (count: number) => {
  if (count === 0) return 'bg-[#F0F2F5] border-[0.4px] border-[#E1E3EF]'
  if (count <= 5 && count > 0) return 'bg-[#E1F9E9] border-[0.4px] border-[#BAEFD1]'
  if (count <= 10 && count > 5) return 'bg-[#78DDA4] border-[0.4px] border-[#3CCB7F]'
  if (count <= 15 && count > 10) return 'bg-[#16B364] border-[0.4px] border-[#099250]'
  return 'bg-[#099250] border-[0.4px] border-[#087443]'
}
export const HeatmapDataOptions = [
  {
    label: 'Todos',
    value: 'todos'
  },
  {
    label: 'Creation',
    value: 'vaults'
  },
  {
    label: 'Context',
    value: 'context'
  },
  {
    label: 'Chat',
    value: 'conversations'
  }
]

export interface MyCustomDayCellProps extends DayCellProps {
  cellSize: number
  myActivityData: Record<string, { count: number }>
  handleSelectDate: (date: string) => void
  selectedDate: string | null
}
const MyCustomDayCell: FC<MyCustomDayCellProps> = (props) => {
  const { date, isEmpty, cellSize, myActivityData, handleSelectDate, selectedDate } = props
  if (isEmpty) {
    return <div style={{ height: cellSize }} className="rounded-[2px]" />
  }

  const dateString = date!.format('YYYY-MM-DD')
  const data = myActivityData[dateString]
  const count = data ? data.count : 0
  const colorClass = getColor(count)

  return (
    <div
      style={{ height: cellSize }}
      className={clsx(`${colorClass}`, 'rounded-[2px] cursor-pointer', {
        'opacity-80': selectedDate && dateString !== selectedDate
      })}
      onClick={() => handleSelectDate(dateString)}
    />
  )
}
export enum MonthType {
  YEAR = 'year',
  MONTH = 'month'
}
export interface HeatmapEntryProps {
  onChange: (date: string | null, monthType: MonthType) => void
}
const HeatmapEntry: FC<HeatmapEntryProps> = (props) => {
  const { onChange } = props
  const { data, loading } = useRequest(async () => {
    const res = await window.dbAPI.getHeatmapData(dayjs('2025-01-01').valueOf(), dayjs('2025-12-31').valueOf())

    const dataList = res.reduce(
      (acc, cur) => {
        const todos = get(cur, 'todos', 0)
        const conversations = get(cur, 'conversations', 0)
        const vaults = get(cur, 'vaults', 0)
        const context = get(cur, 'context', 0)
        set(acc, cur.date, {
          count: conversations + vaults + context / 100 + todos,
          conversations,
          vaults,
          context,
          todos
        })
        set(acc, 'totalTodos', get(acc, 'totalTodos', 0) + todos)
        set(acc, 'totalConversations', get(acc, 'totalConversations', 0) + conversations)
        set(acc, 'totalVaults', get(acc, 'totalVaults', 0) + vaults)
        set(acc, 'totalContext', get(acc, 'totalContext', 0) + context)
        set(acc, 'origin', get(acc, 'totalContext', 0) + context)
        return acc
      },
      {} as Record<string, number>
    )

    return dataList
  })
  const yearList = useMemo(() => {
    const currentYear = dayjs().year() // 当前年份
    const targetYear = 2025
    const diff = targetYear - currentYear
    return Array.from({ length: diff + 1 }, (_, i) => currentYear + i)
  }, [])
  const [selectedYear, setSelectedYear] = useState(yearList[0])
  const [selectedDays, setSelectedDays] = useState<string | null>(null)
  const [currentMode, setCurrentMode] = useState<MonthType>(MonthType.YEAR)

  const handleSelectDate = useMemoizedFn((date: string) => {
    setSelectedDays(date)
    setCurrentMode(MonthType.MONTH)
  })
  const currentDetailData = useMemo(() => {
    if (currentMode === MonthType.YEAR) {
      return HeatmapDataOptions.map((item) => {
        const v = get(data, `total${capitalize(item.value)}`, 0)
        return { label: item.label, value: v }
      })
    } else {
      return HeatmapDataOptions.map((item) => ({
        label: item.label,
        value: get(data, `${selectedDays}.${item.value}`, 0)
      }))
    }
  }, [currentMode, data, selectedDays])
  const handleChangeYear = useMemoizedFn(() => {
    setCurrentMode(MonthType.YEAR)
    setSelectedDays(null)
  })
  const handleSubtract = useMemoizedFn(() => {
    const days = dayjs(selectedDays).subtract(1, 'day').format('YYYY-MM-DD')
    if (dayjs(days).isSameOrAfter(dayjs('2025-01-01'))) {
      setSelectedDays(days)
    } else {
      Message.info('Cannot select past date')
    }
  })

  const handleAdd = useMemoizedFn(() => {
    const days = dayjs(selectedDays).add(1, 'day').format('YYYY-MM-DD')
    if (dayjs(days).isSameOrBefore(dayjs())) {
      setSelectedDays(days)
    } else {
      Message.info('Cannot select future date')
    }
  })
  const [visible, setVisible] = useState(false)
  const handleOpenSelect = useMemoizedFn(() => {
    setVisible(!visible)
  })
  useEffect(() => {
    onChange(selectedDays, currentMode)
  }, [selectedDays, currentMode, onChange])

  return (
    <div className="w-full">
      <div className="flex items-center justify-between w-full">
        {currentMode === MonthType.YEAR ? (
          <Trigger
            trigger="click"
            popupVisible={visible}
            popup={() => (
              <div className="shadow-[0px_5px_15px_0px_rgba(0,0,0,0.052)] p-[6px] rounded-[8px] bg-[#FFFFFF]">
                {yearList.map((year) => (
                  <div
                    key={year}
                    onClick={() => {
                      setSelectedYear(year)
                      handleChangeYear()
                      setVisible(false)
                    }}
                    className="text-[13px] leading-[22px]  text-[#0C0D0E] cursor-pointer px-[12px] py-[5px] hover:bg-[#F6F8FA] rounded-[8px]">
                    {year}
                  </div>
                ))}
              </div>
            )}>
            <div className="flex items-center gap-[4px] text-[#0B0B0F] cursor-pointer" onClick={handleOpenSelect}>
              <div className="text-[16px] leading-[24px] font-medium text-[#0B0B0F]">{selectedYear}</div>
              <IconDown
                className={clsx('text-[#0B0B0F] text-[12px] transition-all duration-200', { 'rotate-180': visible })}
              />
            </div>
          </Trigger>
        ) : (
          <div className="flex items-center gap-[8px] cursor-pointer">
            <div
              onClick={handleChangeYear}
              className="rounded-[4px] flex items-center justify-center text-[12px] leading-[20px] font-medium text-[#3F3F51] bg-[#FFFFFF] border border-[#E1E3EF] px-[12px] py-[2px]">
              Back
            </div>
            <div className="flex items-center gap-[6px]">
              <div
                className="w-[24px] h-[24px] flex items-center justify-center rounded-[4px] bg-[#F6F7FA] text-[#0b0b0f]"
                onClick={handleSubtract}>
                <IconLeft />
              </div>
              <div className="text-[16px] leading-[24px] font-medium text-[#0b0b0f]">
                {dayjs(selectedDays).format('MMMM D, YYYY')}
              </div>
              <div
                className="w-[24px] h-[24px] flex items-center justify-center rounded-[4px] bg-[#F6F7FA] text-[#0b0b0f]"
                onClick={handleAdd}>
                <IconRight />
              </div>
            </div>
          </div>
        )}
        <div className="flex items-center gap-[6px]">
          <span className="text-[10px] leading-[24px] text-[#6E718C]">Less</span>
          <div className="flex items-center gap-[2px]">
            {[0, 5, 10, 15, 20].map((count) => (
              <div key={count} className={`w-[6px] h-[6px] rounded-[1px] ${getColor(count)}`} />
            ))}
          </div>
          <span className="text-[10px] leading-[24px] text-[#6E718C]">More</span>
        </div>
      </div>
      <Divider className="!my-[10px]" />

      <Spin loading={loading} block className="w-full [&_.arco-spin-children]:!w-full">
        <Heatmap
          monthLabelMarginBottom={4}
          weekStartDay="sunday"
          year={selectedYear}
          cellSize={9}
          gap={2}
          renderDay={(props) => (
            <MyCustomDayCell
              {...props}
              cellSize={9}
              myActivityData={data || {}}
              handleSelectDate={handleSelectDate}
              selectedDate={selectedDays}
            />
          )}
          renderWeekday={(props) => {
            const { label, cellSize, index } = props
            return (
              <div
                style={{
                  height: cellSize,
                  justifyContent: 'space-around'
                }} // 使用 cellSize
                className="flex items-center text-xs text-gray-500">
                {index % 2 === 0 ? '' : label}
              </div>
            )
          }}
        />
        <div className="grid grid-cols-4 gap-[8px] mt-[10px]">
          {currentDetailData.map((item) => {
            return (
              <div
                key={item.label}
                className="flex flex-col items-center justify-center py-[8px] rounded-[8px] bg-[#FAFBFD] gap-[4px]">
                <div className="text-[18px] leading-[24px] font-medium text-[#0b0b0f]">
                  {new Intl.NumberFormat().format(item.value)}
                </div>
                <div className="text-[12px] leading-[20px] text-[#6E718C]">{item.label}</div>
              </div>
            )
          })}
        </div>
      </Spin>
    </div>
  )
}
export { HeatmapEntry }
