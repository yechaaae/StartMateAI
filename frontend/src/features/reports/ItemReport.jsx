import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

export const ItemReport = ({ data, go, selectedIdeaRank, onSelectIdea }) => (
  <div className="report-stack">
    <Card>
      <div className="map-box"><Icon name="pin" size={32} /></div>
      <h3>{data.location} 상권 분석</h3>
      <div className="metric-grid">
        {data.analysis.map(([label, value]) => (
          <div key={label}>
            <small>{label}</small>
            <b>{value}</b>
          </div>
        ))}
      </div>
    </Card>

    <Card>
      <h3>상권 + 내 프로필 기반 추천</h3>
      {data.items.map((item) => {
        const selected = selectedIdeaRank === item.rank
        return (
          <button
            key={item.rank}
            className={selected ? 'idea-option selected' : 'idea-option'}
            onClick={() => onSelectIdea?.(item.rank)}
          >
            <span>{item.rank}</span>
            <div>
              <b>{item.title}</b>
              <p>{item.reason}</p>
            </div>
            <em>적합도 {item.score}</em>
          </button>
        )
      })}
      <button className="primary-wide" onClick={() => go('simulator')}>
        선택한 아이템으로 시뮬레이션
        <Icon name="arrow" size={16} />
      </button>
    </Card>
  </div>
)
