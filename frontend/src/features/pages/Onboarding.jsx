import { useState } from 'react'
import { profile } from '../../shared/data/profile'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { BrandMark } from '../../shared/components/BrandMark'

export const Onboarding = ({ go }) => {
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const finish = () => {
    setLoading(true)
    window.setTimeout(() => go('home'), 1300)
  }
  const steps = [
    ['기본 역량과 경력', ['전공 또는 보유 역량', '경력', '강점 태그']],
    ['관심 분야와 지역', ['관심 분야', '거주 지역', '창업 희망 지역']],
    ['자금과 팀 구성', ['초기 자금', '팀 구성', '선호 창업 형태']],
  ]
  if (loading) return <main className="loading-page"><AgentAvatar id="profile" size={64} active /><h2>Profile Agent가 창업 적합도를 진단하고 있어요</h2><p>프로필을 분석해 강점, 리스크, 추천 방향을 정리합니다.</p></main>
  return (
    <main className="onboarding">
      <div className="onboarding-card">
        <div className="brand-line"><BrandMark /><b>창업 프로필 입력</b></div>
        <div className="progress">{[0, 1, 2].map((i) => <span key={i} className={i <= step ? 'on' : ''} />)}</div>
        <small>{step + 1} / 3 단계</small>
        <h1>{steps[step][0]}</h1>
        <p>AI가 개인화된 창업 분석을 할 수 있도록 기본 조건을 알려주세요.</p>
        <div className="form-grid">{steps[step][1].map((label) => <label key={label}>{label}<input defaultValue={label.includes('자금') ? profile.capital : label.includes('지역') ? profile.region : ''} placeholder={label} /></label>)}</div>
        <div className="form-actions">
          {step > 0 && <button onClick={() => setStep(step - 1)}>이전</button>}
          <button onClick={() => step < 2 ? setStep(step + 1) : finish()}>{step < 2 ? '다음' : '프로필 저장하고 진단받기'}</button>
        </div>
      </div>
    </main>
  )
}
