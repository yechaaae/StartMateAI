import { useState } from 'react'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { BrandMark } from '../../shared/components/BrandMark'
import { Icon } from '../../shared/components/Icon'
import { startupProfileApi } from '../../shared/api/client'

const teamStatusOptions = [
  ['SOLO', '개인 창업'],
  ['HAS_TEAM', '팀 보유'],
  ['LOOKING_FOR_TEAM', '팀원 모집 중'],
  ['UNDECIDED', '아직 미정'],
]

const businessTypeOptions = [
  ['ONLINE', '온라인'],
  ['OFFLINE', '오프라인'],
  ['PLATFORM', '플랫폼'],
  ['LOCAL_STORE', '소상공인 매장'],
  ['HYBRID', '온오프라인 병행'],
  ['UNDECIDED', '아직 미정'],
]

const initialForm = {
  major: '',
  career: '',
  interestField: '',
  residenceRegion: '',
  businessRegion: '',
  initialBudget: '',
  teamStatus: 'SOLO',
  preferredBusinessType: 'ONLINE',
  strengthTags: '',
}

export const Onboarding = ({ onComplete }) => {
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setSaving(true)

    try {
      const profile = await startupProfileApi.save({
        ...form,
        initialBudget: Number(form.initialBudget),
      })
      setSaved(true)
      window.setTimeout(() => onComplete(profile), 700)
    } catch (profileError) {
      setError(profileError.message)
    } finally {
      setSaving(false)
    }
  }

  if (saved) {
    return (
      <main className="loading-page">
        <AgentAvatar id="profile" size={64} active />
        <h2>창업 프로필을 저장했어요</h2>
        <p>이제 StartMate AI 작업공간으로 이동합니다.</p>
      </main>
    )
  }

  return (
    <main className="onboarding">
      <section className="onboarding-card">
        <div className="brand-line"><BrandMark /><b>창업 프로필 온보딩</b></div>
        <div className="progress"><span className="on" /><span className="on" /><span className="on" /></div>
        <small>로그인 후 최초 1회 입력</small>
        <h1>맞춤 추천에 필요한 정보를 알려주세요</h1>
        <p>입력한 정보는 아이템 추천, 지원사업 탐색, 사업계획서 초안 생성에 활용됩니다.</p>

        <form onSubmit={submit}>
          <div className="form-grid two-fields">
            <label>
              전공 또는 보유 역량
              <input name="major" value={form.major} onChange={update} placeholder="예: 시각디자인, 개발, 마케팅" required />
            </label>
            <label>
              관심 분야
              <input name="interestField" value={form.interestField} onChange={update} placeholder="예: F&B, 로컬 브랜드, 교육" required />
            </label>
            <label>
              거주 지역
              <input name="residenceRegion" value={form.residenceRegion} onChange={update} placeholder="예: 부산 해운대구" required />
            </label>
            <label>
              창업 희망 지역
              <input name="businessRegion" value={form.businessRegion} onChange={update} placeholder="예: 부산, 서울, 온라인" required />
            </label>
            <label>
              초기 예산
              <input name="initialBudget" type="number" min="0" max="1000000000" value={form.initialBudget} onChange={update} placeholder="예: 3000000" required />
            </label>
            <label>
              팀 구성
              <select name="teamStatus" value={form.teamStatus} onChange={update}>
                {teamStatusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>
              선호 창업 형태
              <select name="preferredBusinessType" value={form.preferredBusinessType} onChange={update}>
                {businessTypeOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>
              경험 또는 경력
              <textarea name="career" value={form.career} onChange={update} rows="4" placeholder="예: 카페 매니저 1년, SNS 채널 운영 경험" required />
            </label>
            <label className="wide-field">
              강점 태그
              <input name="strengthTags" value={form.strengthTags} onChange={update} placeholder="예: 디자인 감각, 실행력, SNS 운영" required />
            </label>
          </div>

          {error && <div className="api-alert">{error}</div>}

          <div className="form-actions">
            <button type="submit" disabled={saving}>
              {saving ? '저장 중...' : '프로필 저장하고 시작하기'} <Icon name="arrow" size={18} />
            </button>
          </div>
        </form>
      </section>
    </main>
  )
}
