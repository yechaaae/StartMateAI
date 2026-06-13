import { useEffect, useMemo, useState } from 'react'
import { agents } from '../../shared/data/agents'
import { features, preStartupFeatures, postStartupFeatures } from '../../shared/data/features'
import { savedResultApi, startupProfileApi } from '../../shared/api/client'
import { categoryLabel } from '../../shared/data/itemCategory'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'
import { WorkspaceChat } from './WorkspaceChat'

const formatKrw = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return null
  if (value >= 10000) return `${Math.round(value / 10000).toLocaleString('ko-KR')}만 원`
  return `${value.toLocaleString('ko-KR')}원`
}

export const HomePage = ({ go, workspace, user }) => {
  const [profile, setProfile] = useState(null)
  const [itemReport, setItemReport] = useState(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    startupProfileApi.get().then(setProfile)
    savedResultApi.latest('ITEM').then(setItemReport).catch(() => setItemReport(null))
  }, [])

  // 저장된 아이템 리포트에서 선택한 아이템을 뽑는다. 없으면 워크스페이스 4필드로 폴백한다.
  const { item, hasDetail } = useMemo(() => {
    const reportData = itemReport?.payload?.reportData
    const items = Array.isArray(reportData?.items) ? reportData.items : []
    const matchesWorkspace =
      !workspace?.id || !itemReport?.workspaceId || String(itemReport.workspaceId) === String(workspace.id)
    if (matchesWorkspace && items.length) {
      const rank = itemReport?.payload?.viewState?.selectedIdeaRank
      const picked = items.find((it) => it.rank === rank) ?? items[0]
      return { item: picked, hasDetail: true }
    }
    const ws = workspace?.selectedIdea
    if (ws?.title) {
      return { item: { title: ws.title, category: ws.category, score: ws.score, reason: ws.reason }, hasDetail: false }
    }
    return { item: null, hasDetail: false }
  }, [itemReport, workspace])

  if (!profile) return <main className="page workspace-page">로딩 중...</main>

  const profileItems = [
    ['전공', profile.major],
    ['경력', profile.career],
    ['관심 분야', profile.interestField],
    ['거주 지역', profile.residenceRegion],
    ['초기 자금', profile.initialBudget ? `${(profile.initialBudget / 10000).toFixed(0)}만 원` : '-'],
    ['팀 구성', profile.teamStatusLabel],
    ['창업 형태', profile.preferredBusinessTypeLabel],
  ]

  return (
    <main className="page workspace-page">
      <div className="page-title">
        <div>
          <h1>{workspace?.name ?? '내 워크스페이스'}</h1>
          <p>이 워크스페이스에서의 기능은 이 프로필과 아이템을 기준으로 동작합니다.</p>
        </div>
      </div>

      <div className="workspace-summary-grid">
        <Card className="profile-summary-card">
          <div className="summary-card-head">
            <div className="summary-title">
              <span><Icon name="user" size={17} /></span>
              <h3>입력한 프로필</h3>
            </div>
            <button onClick={() => go('onboarding')}>
              <Icon name="edit" size={14} />
              수정
            </button>
          </div>

          <div className="profile-summary-grid">
            {profileItems.map(([label, value]) => (
              <div key={label}>
                <small>{label}</small>
                <b>{value}</b>
              </div>
            ))}
          </div>

          <div className="profile-tag-section">
            <small>강점</small>
            <div className="profile-tags">
              {profile.strengthTags?.split(',').map((tag) => <span key={tag.trim()}>{tag.trim()}</span>)}
            </div>
          </div>
        </Card>

        <ItemSummaryCard
          item={item}
          hasDetail={hasDetail}
          expanded={expanded}
          onToggle={() => setExpanded((v) => !v)}
          go={go}
        />
      </div>

      <div className="feature-section-head">
        <span>창업 전</span>
        <b>{preStartupFeatures.length}</b>
        <i />
      </div>
      <div className="feature-grid feature-grid-3">
        {preStartupFeatures.map((id) => <FeatureCard key={id} id={id} go={go} />)}
      </div>

      <div className="feature-section-head section-gap">
        <span>창업 후</span>
        <b>{postStartupFeatures.length}</b>
        <i />
      </div>
      <div className="feature-grid feature-grid-3">
        {postStartupFeatures.map((id) => <FeatureCard key={id} id={id} go={go} />)}
      </div>

      <WorkspaceChat user={user} go={go} />
    </main>
  )
}

const ItemSummaryCard = ({ item, hasDetail, expanded, onToggle, go }) => {
  if (!item) {
    return (
      <Card className="item-summary-card">
        <div className="summary-card-head">
          <div className="summary-title">
            <span><Icon name="bulb" size={17} /></span>
            <h3>추천 아이템</h3>
          </div>
        </div>
        <p className="item-summary-empty">아직 선택된 창업 아이템이 없어요. 아이템 추천부터 시작해보세요.</p>
        <button type="button" className="item-detail-toggle" onClick={() => go('item')}>
          아이템 추천 받기 <Icon name="arrow" size={14} />
        </button>
      </Card>
    )
  }

  return (
    <Card className="item-summary-card">
      <div className="summary-card-head">
        <div className="summary-title">
          <span><Icon name="bulb" size={17} /></span>
          <h3>추천 아이템</h3>
        </div>
        {item.score != null && <span className="item-summary-score">AI 추천 점수 {item.score}</span>}
      </div>

      <div className="item-summary-body">
        <b className="item-summary-title">{item.title}</b>
        {item.category && <span className="item-summary-cat">{categoryLabel(item.category)}</span>}
        {item.reason && <p className="item-summary-reason">{item.reason}</p>}
      </div>

      {hasDetail ? (
        <>
          <button type="button" className="item-detail-toggle" onClick={onToggle}>
            {expanded ? '상세 닫기' : '상세보기'}
            <Icon
              name="chevron"
              size={14}
              style={{ transform: expanded ? 'rotate(-90deg)' : 'rotate(90deg)', transition: 'transform .15s' }}
            />
          </button>
          {expanded && <ItemDetail item={item} />}
        </>
      ) : (
        <p className="item-summary-note">상세 근거와 실행 방안은 아이템 리포트에서 확인할 수 있어요.</p>
      )}
    </Card>
  )
}

const ItemDetail = ({ item }) => {
  const evidence = Array.isArray(item.evidence) ? item.evidence : []
  const analysis = Array.isArray(item.analysis) ? item.analysis : []
  const supportPrograms = Array.isArray(item.supportPrograms) ? item.supportPrograms : []
  const first30Days = Array.isArray(item.first30Days) ? item.first30Days : []
  const risks = Array.isArray(item.risks) ? item.risks : []
  const breakdown = item.scoreBreakdown && typeof item.scoreBreakdown === 'object' ? item.scoreBreakdown : null
  const commercial = item.commercialArea && typeof item.commercialArea === 'object' ? item.commercialArea : null
  const cost = formatKrw(item.estimatedInitialCost)

  return (
    <div className="item-detail">
      <section className="item-detail-section">
        <h4>추천 근거</h4>
        {!!evidence.length && (
          <ul className="item-detail-bullets">
            {evidence.map((line, i) => <li key={i}>{line}</li>)}
          </ul>
        )}
        {breakdown && (
          <div className="metric-grid">
            <div><small>기본 적합도</small><b>{breakdown.base_score ?? '-'}점</b></div>
            {breakdown.commercial_area_adjustment ? <div><small>상권 보정</small><b>{breakdown.commercial_area_adjustment > 0 ? '+' : ''}{breakdown.commercial_area_adjustment}</b></div> : null}
            {breakdown.support_program_adjustment ? <div><small>지원사업 보정</small><b>{breakdown.support_program_adjustment > 0 ? '+' : ''}{breakdown.support_program_adjustment}</b></div> : null}
            <div><small>최종 점수</small><b>{breakdown.grounded_score ?? item.score ?? '-'}점</b></div>
          </div>
        )}
        {!!analysis.length && (
          <div className="metric-grid">
            {analysis.map(([label, value], i) => (
              <div key={`${label}-${i}`}><small>{label}</small><b>{value}</b></div>
            ))}
          </div>
        )}
        {commercial && (commercial.competitionLevel || commercial.directCompetitors != null) && (
          <p className="item-detail-line">
            상권 경쟁도 {commercial.competitionLevel ?? '-'}
            {commercial.directCompetitors != null ? ` · 직접 경쟁점 ${Number(commercial.directCompetitors).toLocaleString('ko-KR')}개` : ''}
          </p>
        )}
        {!!supportPrograms.length && (
          <div className="item-detail-support">
            <Icon name="doc" size={13} />
            <span>{supportPrograms[0].title}{supportPrograms[0].score != null ? ` (${supportPrograms[0].score}점)` : ''}</span>
          </div>
        )}
      </section>

      <section className="item-detail-section">
        <h4>추천 아이템 상세 방안</h4>
        {(cost || item.feasibilityLabel) && (
          <p className="item-detail-line">
            {cost ? `예상 초기자금 ${cost}` : ''}
            {cost && item.feasibilityLabel ? ' · ' : ''}
            {item.feasibilityLabel ? `실행성 ${item.feasibilityLabel}` : ''}
          </p>
        )}
        {item.validationMethod && (
          <p className="item-detail-line"><b>검증 방법</b> {item.validationMethod}</p>
        )}
        {!!first30Days.length && (
          <>
            <small className="item-detail-label">30일 실행 계획</small>
            <ol className="item-detail-steps">
              {first30Days.map((step, i) => <li key={i}>{step}</li>)}
            </ol>
          </>
        )}
        {!!risks.length && (
          <>
            <small className="item-detail-label">유의할 리스크</small>
            <ul className="item-detail-bullets warn">
              {risks.map((risk, i) => <li key={i}>{risk}</li>)}
            </ul>
          </>
        )}
      </section>
    </div>
  )
}

export const FeatureCard = ({ id, go }) => {
  const f = features[id]
  const a = agents[f.agent]

  return (
    <button className="feature-card" onClick={() => go(id)} style={{ '--accent': a.color, '--tint': a.tint }}>
      <div className="feature-card-head">
        <span><Icon name={f.icon} size={18} /></span>
        <small>{f.flag}</small>
      </div>
      <h3>{f.title}</h3>
      <p>{f.card}</p>
      <b>기능 사용하기</b>
    </button>
  )
}
