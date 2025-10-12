import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface CandleData {
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface StockChartProps {
  symbol: string
  candles: { [timestamp: string]: CandleData }
}

const StockChart: React.FC<StockChartProps> = ({ symbol, candles }) => {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current) return

    // Initialize chart
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, 'dark')
    }

    // Cleanup on unmount
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose()
        chartInstance.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!chartInstance.current || !candles || Object.keys(candles).length === 0) return

    // Prepare data for ECharts
    const sortedEntries = Object.entries(candles).sort(([a], [b]) => a.localeCompare(b))

    const dates = sortedEntries.map(([timestamp]) => {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      })
    })

    const candlestickData = sortedEntries.map(([, candle]) => [
      candle.open,
      candle.close,
      candle.low,
      candle.high
    ])

    const volumeData = sortedEntries.map(([, candle]) => candle.volume)

    const option = {
      title: {
        text: `${symbol} - Live Stock Data`,
        left: 'center',
        textStyle: {
          color: '#ffffff',
          fontSize: 18
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: '#777',
        formatter: function (params: any) {
          const data = params[0]
          const volumeData = params[1]
          const candleData = data.data

          return `
            <div style="padding: 10px;">
              <div style="margin-bottom: 8px; font-weight: bold; color: #61dafb;">
                ${symbol} - ${data.axisValue}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #4CAF50;">Open:</span> $${candleData[0].toFixed(2)}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #4CAF50;">High:</span> $${candleData[3].toFixed(2)}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #f44336;">Low:</span> $${candleData[2].toFixed(2)}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: ${candleData[1] >= candleData[0] ? '#4CAF50' : '#f44336'};">Close:</span> $${candleData[1].toFixed(2)}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #ff9800;">Volume:</span> ${volumeData ? volumeData.data.toLocaleString() : 'N/A'}
              </div>
            </div>
          `
        }
      },
      legend: {
        data: ['Candlestick', 'Volume'],
        textStyle: {
          color: '#ffffff'
        }
      },
      grid: [
        {
          left: '10%',
          right: '8%',
          top: '12%',
          height: '48%'
        },
        {
          left: '10%',
          right: '8%',
          top: '65%',
          height: '15%',
          bottom: '15%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          boundaryGap: true,
          axisLine: { lineStyle: { color: '#777' } },
          axisLabel: { color: '#ffffff' }
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          boundaryGap: true,
          axisLine: { lineStyle: { color: '#777' } },
          axisLabel: { color: '#ffffff' }
        }
      ],
      yAxis: [
        {
          scale: true,
          axisLine: { lineStyle: { color: '#777' } },
          axisLabel: { color: '#ffffff' },
          splitLine: { lineStyle: { color: '#333' } }
        },
        {
          scale: true,
          gridIndex: 1,
          axisLine: { lineStyle: { color: '#777' } },
          axisLabel: { color: '#ffffff' },
          splitLine: { lineStyle: { color: '#333' } }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: dates.length > 20 ? ((dates.length - 20) / dates.length) * 100 : 0,
          end: 100
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          bottom: '1%',
          height: 25,
          start: dates.length > 20 ? ((dates.length - 20) / dates.length) * 100 : 0,
          end: 100,
          textStyle: { color: '#ffffff' },
          handleStyle: {
            color: '#61dafb'
          },
          borderColor: '#444',
          fillerColor: 'rgba(97, 218, 251, 0.2)',
          dataBackground: {
            lineStyle: { color: '#61dafb' },
            areaStyle: { color: 'rgba(97, 218, 251, 0.1)' }
          }
        }
      ],
      series: [
        {
          name: 'Candlestick',
          type: 'candlestick',
          data: candlestickData,
          barMaxWidth: 50,
          barCategoryGap: '2px',  // Fixed pixel gap
          itemStyle: {
            color: '#4CAF50',      // Rising candles (green)
            color0: '#f44336',     // Falling candles (red)
            borderColor: '#4CAF50',
            borderColor0: '#f44336',
            borderWidth: 1,
            borderType: 'solid'
          },
          emphasis: {
            itemStyle: {
              color: '#66BB6A',
              color0: '#ef5350',
              borderColor: '#66BB6A',
              borderColor0: '#ef5350',
              borderWidth: 2
            }
          }
        },
        {
          name: 'Volume',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumeData,
          barMaxWidth: 50,
          barCategoryGap: '2px',  // Match candlestick gap
          itemStyle: {
            color: function(params: any) {
              const index = params.dataIndex
              if (index === 0) return '#ff9800'

              const currentCandle = candlestickData[index]
              const prevCandle = candlestickData[index - 1]

              if (currentCandle && prevCandle) {
                return currentCandle[1] >= prevCandle[1] ? '#4CAF50' : '#f44336'
              }
              return '#ff9800'
            }
          }
        }
      ]
    }

    // Use notMerge: false to allow smooth updates
    chartInstance.current.setOption(option, { notMerge: false, lazyUpdate: false })

    // Handle window resize
    const handleResize = () => {
      if (chartInstance.current) {
        chartInstance.current.resize()
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)

  }, [symbol, candles])

  return (
    <div
      ref={chartRef}
      style={{
        width: '100%',
        height: '600px',
        minHeight: '600px',
        border: '1px solid #444',
        borderRadius: '8px',
        backgroundColor: '#1a1a1a',
        boxSizing: 'border-box'
      }}
    />
  )
}

export default StockChart