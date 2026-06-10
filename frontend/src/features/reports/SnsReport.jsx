import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

const CHANNEL_OPTIONS = [
  ['INSTAGRAM_REELS', '인스타 릴스'],
  ['INSTAGRAM_POST', '인스타 피드'],
  ['BLOG_POST', '블로그'],
  ['SHORTS', '유튜브 쇼츠'],
]

const TONE_OPTIONS = [
  ['FRIENDLY', '친근한 톤'],
  ['EXPERT', '전문가 톤'],
  ['TRENDY', '트렌디 톤'],
  ['TRUSTED', '신뢰형 톤'],
]

const OBJECTIVE_OPTIONS = [
  ['CONVERSION', '예약/구매 전환'],
  ['AWARENESS', '브랜드 인지도'],
  ['REVISIT', '재방문 유도'],
  ['EVENT', '이벤트 홍보'],
]

const updateBeat = (setData, index, nextValue) => {
  setData((current) => ({
    ...current,
    beats: current.beats.map((beat, beatIndex) => (beatIndex === index ? nextValue : beat)),
  }))
}

export const SnsReport = ({ data, setData }) => (
  <Card>
    <div className="card-head">
      <h3>SNS 캠페인 초안</h3>
      <button type="button">채널별 조정</button>
    </div>

    <div className="support-control-block">
      <small>캠페인 목적</small>
      <div className="support-control-row">
        {OBJECTIVE_OPTIONS.map(([value, label]) => (
          <button
            key={value}
            className={data.objective === value ? 'support-filter on' : 'support-filter'}
            onClick={() => setData((current) => ({ ...current, objective: value }))}
          >
            {label}
          </button>
        ))}
      </div>
    </div>

    <div className="support-control-block">
      <small>채널</small>
      <div className="support-control-row">
        {CHANNEL_OPTIONS.map(([value, label]) => (
          <button
            key={value}
            className={data.channel === value ? 'support-filter on' : 'support-filter'}
            onClick={() => setData((current) => ({ ...current, channel: value }))}
          >
            {label}
          </button>
        ))}
      </div>
    </div>

    <div className="support-control-block">
      <small>톤</small>
      <div className="support-control-row">
        {TONE_OPTIONS.map(([value, label]) => (
          <button
            key={value}
            className={data.tone === value ? 'support-filter on' : 'support-filter'}
            onClick={() => setData((current) => ({ ...current, tone: value }))}
          >
            {label}
          </button>
        ))}
      </div>
    </div>

    <div className="sns-preview">
      <div>
        <Icon name="play" />
        <label className="operation-field">
          <small>콘텐츠 주제</small>
          <input
            value={data.topic}
            onChange={(event) => setData((current) => ({ ...current, topic: event.target.value }))}
          />
        </label>
        <label className="operation-field">
          <small>후킹 문구</small>
          <textarea
            value={data.hook}
            onChange={(event) => setData((current) => ({ ...current, hook: event.target.value }))}
            rows="4"
          />
        </label>
      </div>

      <section>
        <h3>15초 영상 구성</h3>
        {data.beats.map((beat, index) => (
          <label key={`${beat}-${index}`} className="operation-field">
            <small>장면 {index + 1}</small>
            <input
              value={beat}
              onChange={(event) => updateBeat(setData, index, event.target.value)}
            />
          </label>
        ))}

        <label className="operation-field sns-tag-field">
          <small>해시태그</small>
          <input
            value={data.tags.join(', ')}
            onChange={(event) => setData((current) => ({
              ...current,
              tags: event.target.value.split(',').map((tag) => tag.trim()).filter(Boolean),
            }))}
          />
        </label>

        <div className="tags">
          {data.tags.map((tag) => <span key={tag}>{tag}</span>)}
        </div>

        <label className="operation-field">
          <small>CTA</small>
          <input
            value={data.callToAction ?? ''}
            onChange={(event) => setData((current) => ({ ...current, callToAction: event.target.value }))}
            placeholder="예: 지금 예약 주문하기"
          />
        </label>

        <button className="primary-wide">
          <Icon name="clock" size={16} /> {data.schedule} 게시 예약
        </button>
      </section>
    </div>
  </Card>
)
