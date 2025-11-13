import { Tooltip } from '@arco-design/web-react'
import { Heatmap, DayCellProps } from '@zhongyao/heatmap'

// 假设你从 API 获取了这样的数据
const myActivityData: Record<string, { count: number }> = {
  '2024-01-15': { count: 5 },
  '2024-01-16': { count: 2 },
  '2024-01-18': { count: 12 }
  // ...
}

// 1. 创建一个函数来获取颜色
const getColor = (count: number) => {
  if (count === 0) return 'bg-gray-100'
  if (count < 3) return 'bg-green-200'
  if (count < 8) return 'bg-green-400'
  return 'bg-green-600'
}

// 2. 创建你的自定义日期单元格组件
const MyCustomDayCell = ({ date, isEmpty, cellSize }: DayCellProps & { cellSize: number }) => {
  if (isEmpty) {
    return <div style={{ width: cellSize, height: cellSize }} />
  }

  const dateString = date!.format('YYYY-MM-DD')
  const data = myActivityData[dateString]
  const count = data ? data.count : 0
  const colorClass = getColor(count)

  return (
    <Tooltip content={`${dateString}: ${count} contributions`}>
      <div
        style={{ width: cellSize, height: cellSize }}
        className={`${colorClass} rounded hover:outline hover:outline-blue-500`}
      />
    </Tooltip>
  )
}

// 3. 将它作为 prop 传入
const HeatmapEntry = () => (
  <Heatmap year={2024} cellSize={14} gap={3} renderDay={(props) => <MyCustomDayCell {...props} cellSize={14} />} />
)
export { HeatmapEntry }
