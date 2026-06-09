import { Card } from '../../shared/components/Card'

export const SimReport = ({ data }) => {
  const series = Array.from({ length: 4 }, (_, i) => {
    const day = [1, 7, 15, 30][i]
    const revenue = Math.round(data.startOrders * data.price * (1 + i * data.growthPct / 100))
    return [day, revenue]
  })
  return <Card><h3>첫 30일 시뮬레이션</h3><div className="sim-inputs"><span>{data.item}</span><span>판매가 {data.price.toLocaleString()}원</span><span>초기자금 {data.capital}만 원</span></div><div className="sim-chart">{series.map(([day, revenue]) => <div key={day}><i style={{ height: `${Math.max(22, revenue / 800)}px` }} /><b>Day {day}</b><span>{Math.round(revenue / 10000)}만 원</span></div>)}</div><div className="tags warn">{data.risks.map((r) => <span key={r}>{r}</span>)}</div></Card>
}
