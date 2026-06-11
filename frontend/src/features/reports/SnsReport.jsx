import { useEffect, useMemo, useState } from 'react'
import { threadsApi } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

const TONE_OPTIONS = [
  ['FRIENDLY', '친근하게'],
  ['EXPERT', '전문적으로'],
  ['TRENDY', '트렌디하게'],
  ['TRUSTED', '신뢰감 있게'],
]

const OBJECTIVE_OPTIONS = [
  ['CONVERSION', '방문/예약 유도'],
  ['AWARENESS', '브랜드 알리기'],
  ['REVISIT', '재방문 유도'],
  ['EVENT', '이벤트 홍보'],
]

const buildThreadText = (data) => {
  const tags = (data.tags ?? [])
    .map((tag) => tag.startsWith('#') ? tag : `#${tag.replace(/\s+/g, '')}`)
    .join(' ')

  return [
    data.hook,
    '',
    data.topic ? `오늘 소개할 아이템은 ${data.topic}입니다.` : '',
    data.callToAction,
    tags,
  ].filter(Boolean).join('\n')
}

const Chip = ({ active, children, onClick }) => (
  <button
    type="button"
    className={active ? 'sns-chip on' : 'sns-chip'}
    onClick={onClick}
  >
    {children}
  </button>
)

export const SnsReport = ({ data, setData }) => {
  const [account, setAccount] = useState({ connected: false })
  const [logs, setLogs] = useState([])
  const [draftText, setDraftText] = useState(() => buildThreadText(data))
  const [loading, setLoading] = useState(true)
  const [publishing, setPublishing] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const recommendedText = useMemo(() => buildThreadText(data), [data])
  const remaining = 500 - draftText.length

  useEffect(() => {
    let active = true

    const load = async () => {
      try {
        setLoading(true)
        setError('')
        const [accountResponse, logsResponse] = await Promise.all([
          threadsApi.account(),
          threadsApi.logs(),
        ])
        if (!active) return
        setAccount(accountResponse)
        setLogs(logsResponse.logs ?? [])
      } catch (nextError) {
        if (!active) return
        setError(nextError.message ?? 'Threads 상태를 불러오지 못했습니다.')
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    setDraftText((current) => current || recommendedText)
  }, [recommendedText])

  const updateTags = (value) => {
    setData((current) => ({
      ...current,
      tags: value.split(',').map((tag) => tag.trim()).filter(Boolean),
    }))
  }

  const connectThreads = async () => {
    try {
      setError('')
      const response = await threadsApi.connectUrl()
      window.location.href = response.url
    } catch (nextError) {
      setError(nextError.message ?? 'Threads 연결 URL을 만들지 못했습니다.')
    }
  }

  const publish = async () => {
    if (publishing || !draftText.trim()) return

    try {
      setPublishing(true)
      setMessage('')
      setError('')
      const response = await threadsApi.publish({ text: draftText })
      setMessage(`Threads 게시 완료: ${response.platformPostId}`)
      const logsResponse = await threadsApi.logs()
      setLogs(logsResponse.logs ?? [])
    } catch (nextError) {
      setError(nextError.message ?? 'Threads 게시에 실패했습니다.')
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className="sns-report-stack">
      <Card className="sns-automation-card">
        <div className="sns-report-head">
          <div className="sns-title-row">
            <span className="sns-title-icon"><Icon name="megaphone" size={20} /></span>
            <div>
              <h3>Threads 홍보 자동화</h3>
              <p>창업 아이템을 바탕으로 홍보글을 만들고 연결된 계정에 바로 게시해요.</p>
            </div>
          </div>
          <button type="button" className="sns-soft-button" onClick={() => setDraftText(recommendedText)}>
            <Icon name="refresh" size={14} />
            초안 다시 채우기
          </button>
        </div>

        <div className="sns-report-body">
          <div className="sns-control-block">
            <small>캠페인 목적</small>
            <div>
              {OBJECTIVE_OPTIONS.map(([value, label]) => (
                <Chip
                  key={value}
                  active={data.objective === value}
                  onClick={() => setData((current) => ({ ...current, objective: value }))}
                >
                  {label}
                </Chip>
              ))}
            </div>
          </div>

          <div className="sns-control-block">
            <small>톤</small>
            <div>
              {TONE_OPTIONS.map(([value, label]) => (
                <Chip
                  key={value}
                  active={data.tone === value}
                  onClick={() => setData((current) => ({ ...current, tone: value }))}
                >
                  {label}
                </Chip>
              ))}
            </div>
          </div>

          <div className="sns-publish-layout">
            <section className="sns-compose-panel">
              <label className="operation-field">
                <small>홍보 주제</small>
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
                  rows="3"
                />
              </label>

              <label className="operation-field">
                <small>CTA</small>
                <input
                  value={data.callToAction ?? ''}
                  onChange={(event) => setData((current) => ({ ...current, callToAction: event.target.value }))}
                  placeholder="지금 예약 주문하기"
                />
              </label>

              <label className="operation-field sns-tag-field">
                <small>해시태그</small>
                <input
                  value={(data.tags ?? []).join(', ')}
                  onChange={(event) => updateTags(event.target.value)}
                />
              </label>

              <div className="sns-tag-list">
                {(data.tags ?? []).map((tag) => (
                  <span key={tag}>{tag.startsWith('#') ? tag : `#${tag}`}</span>
                ))}
              </div>
            </section>

            <section className="sns-publish-panel">
              <div className="sns-account-box">
                <div>
                  <small>Threads 계정</small>
                  <b>
                    {loading
                      ? '확인 중'
                      : account.connected
                        ? `@${account.username || account.platformUserId}`
                        : '연결 필요'}
                  </b>
                </div>
                <button type="button" onClick={connectThreads}>
                  {account.connected ? '다시 연결' : '계정 연결'}
                </button>
              </div>

              <label className="operation-field sns-thread-field">
                <small>게시 문구</small>
                <textarea
                  className="sns-thread-textarea"
                  value={draftText}
                  onChange={(event) => setDraftText(event.target.value)}
                  rows="9"
                />
              </label>

              <div className={remaining < 0 ? 'sns-counter warn' : 'sns-counter'}>
                {remaining}자 남음
              </div>

              {!!message && <div className="sns-status success"><Icon name="check" size={16} />{message}</div>}
              {!!error && <div className="sns-status error">{error}</div>}

              <button
                className="sns-publish-button"
                onClick={publish}
                disabled={!account.connected || publishing || remaining < 0 || !draftText.trim()}
              >
                {publishing ? <Icon name="clock" size={17} /> : <Icon name="megaphone" size={17} />}
                {publishing ? '게시 중...' : 'Threads에 바로 게시'}
              </button>
            </section>
          </div>
        </div>
      </Card>

      <Card className="sns-history-card">
        <div className="sns-history-head">최근 게시 기록</div>
        <div className="sns-history-body">
          {!logs.length && <p>아직 게시된 콘텐츠가 없어요.</p>}
          {logs.slice(0, 5).map((log) => (
            <div key={log.id} className="sns-log-row">
              <span className={log.status === 'SUCCESS' ? 'success' : 'error'}>{log.status}</span>
              <p>{log.text}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
