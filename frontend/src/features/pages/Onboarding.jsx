import { useEffect, useRef, useState } from 'react'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { BrandMark } from '../../shared/components/BrandMark'
import { Icon } from '../../shared/components/Icon'
import { startupProfileApi } from '../../shared/api/client'
import {
  getFirstIncompleteOnboardingField,
  getOnboardingProgress,
  getVisibleOnboardingFields,
  isOnboardingStepComplete,
  onboardingStepCount,
} from './onboardingFlow'

const teamStatusOptions = [
  ['SOLO', '개인', '혼자 빠르게 검증하고 있어요'],
  ['HAS_TEAM', '팀 있음', '함께 실행할 멤버가 있어요'],
  ['LOOKING_FOR_TEAM', '팀원 모집 중', '같이 만들 사람을 찾고 있어요'],
  ['UNDECIDED', '아직 미정', '정해진 구성은 없어요'],
]

const businessTypeOptions = [
  ['ONLINE', '온라인', '웹, 앱, 커머스 중심'],
  ['OFFLINE', '오프라인', '공간과 현장 운영 중심'],
  ['PLATFORM', '플랫폼', '공급자와 수요자를 연결'],
  ['LOCAL_STORE', '소상공인 매장', '동네 기반 점포 운영'],
  ['HYBRID', '온오프라인 병행', '온라인과 현장을 함께 운영'],
  ['UNDECIDED', '아직 미정', '추천을 보며 정하고 싶어요'],
]

const initialForm = {
  major: '',
  career: '',
  interestField: '',
  residenceRegion: '',
  businessRegion: '',
  initialBudget: '',
  teamStatus: '',
  preferredBusinessType: '',
  strengthTags: '',
}

const stepCopy = [
  {
    eyebrow: '1단계',
    title: '어떤 창업을 꿈꾸고 계신가요?',
    description: '맞춤 추천을 위해 선호 창업 형태와 팀 구성을 먼저 볼게요.',
  },
  {
    eyebrow: '2단계',
    title: '아이디어의 기본 조건을 알려주세요',
    description: '분야, 지역, 예산을 바탕으로 현실적인 추천을 좁혀갑니다.',
  },
  {
    eyebrow: '3단계',
    title: '나만의 경험과 강점을 더해주세요',
    description: '경험과 강점은 사업 아이디어와 지원사업 매칭 품질을 높여줍니다.',
  },
]

const TextField = ({ targetName, label, name, value, onChange, placeholder, type = 'text', wide = false, ...props }) => (
  <label
    className={wide ? 'onboarding-field wide-field' : 'onboarding-field'}
    data-onboarding-target={targetName}
  >
    <span>{label}</span>
    <input
      name={name}
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      required
      {...props}
    />
  </label>
)

const TextAreaField = ({ targetName, label, name, value, onChange, placeholder }) => (
  <label className="onboarding-field wide-field" data-onboarding-target={targetName}>
    <span>{label}</span>
    <textarea
      name={name}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      rows="4"
      required
    />
  </label>
)

const OptionCard = ({ selected, title, description, onClick }) => (
  <button
    type="button"
    className={selected ? 'onboarding-option selected' : 'onboarding-option'}
    onClick={onClick}
  >
    <span>
      <b>{title}</b>
      <small>{description}</small>
    </span>
    <i><Icon name="check" size={16} /></i>
  </button>
)

export const Onboarding = ({ onComplete }) => {
  const [form, setForm] = useState(initialForm)
  const [stepIndex, setStepIndex] = useState(0)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const flowRef = useRef(null)
  const progress = getOnboardingProgress(stepIndex)
  const step = stepCopy[stepIndex]
  const isLastStep = stepIndex === onboardingStepCount - 1
  const canContinue = isOnboardingStepComplete(stepIndex, form)
  const visibleFields = getVisibleOnboardingFields(stepIndex, form)

  const scrollToTarget = (name, block = 'start') => {
    window.setTimeout(() => {
      flowRef.current?.querySelector(`[data-onboarding-target="${name}"]`)?.scrollIntoView({
        behavior: 'smooth',
        block,
      })
    }, 80)
  }

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
    setError('')
  }

  const select = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setError('')

    if (stepIndex === 0 && name === 'preferredBusinessType' && !form.teamStatus) {
      scrollToTarget('teamStatus', 'center')
    }
  }

  const moveBack = () => {
    if (saved) return
    setError('')
    setStepIndex((current) => Math.max(current - 1, 0))
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')

    if (!canContinue) {
      const firstIncompleteField = getFirstIncompleteOnboardingField(stepIndex, form)
      if (firstIncompleteField) {
        scrollToTarget(firstIncompleteField, 'center')
      }
      return
    }

    if (!isLastStep) {
      setStepIndex((current) => Math.min(current + 1, onboardingStepCount - 1))
      return
    }

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

  useEffect(() => {
    flowRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }, [stepIndex])

  useEffect(() => {
    if (saved) {
      const preventBack = () => {
        window.history.pushState(null, '', window.location.href)
      }
      window.history.pushState(null, '', window.location.href)
      window.addEventListener('popstate', preventBack)
      return () => window.removeEventListener('popstate', preventBack)
    }
  }, [saved])

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
    <main className="onboarding-shell" ref={flowRef}>
      <section className="onboarding-flow">
        <button
          type="button"
          className="onboarding-brand"
          onClick={moveBack}
          disabled={stepIndex === 0 || saved}
        >
          <BrandMark /><b>StartMate AI</b>
        </button>

        <div className="onboarding-progress">
          <span style={{ width: `${progress.percent}%` }} />
        </div>

        <header className="onboarding-flow-head">
          <small>{step.eyebrow} · {progress.current} / {progress.total}</small>
          <h1>{step.title}</h1>
          <p>{step.description}</p>
        </header>

        <form className="onboarding-flow-form" onSubmit={submit}>
          {stepIndex === 0 && (
            <div className="onboarding-step">
              <div className="onboarding-section" data-onboarding-target="preferredBusinessType">
                <h2>선호 창업 형태</h2>
                <div className="onboarding-option-grid two-col">
                  {businessTypeOptions.map(([value, title, description]) => (
                    <OptionCard
                      key={value}
                      selected={form.preferredBusinessType === value}
                      title={title}
                      description={description}
                      onClick={() => select('preferredBusinessType', value)}
                    />
                  ))}
                </div>
              </div>

              {visibleFields.includes('teamStatus') && (
                <div className="onboarding-section reveal-section" data-onboarding-target="teamStatus">
                  <h2>팀 구성</h2>
                  <div className="onboarding-option-grid">
                    {teamStatusOptions.map(([value, title, description]) => (
                      <OptionCard
                        key={value}
                        selected={form.teamStatus === value}
                        title={title}
                        description={description}
                        onClick={() => select('teamStatus', value)}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {stepIndex === 1 && (
            <div className="onboarding-step">
              <div className="onboarding-input-grid">
                <TextField targetName="major" label="전공 또는 보유 역량" name="major" value={form.major} onChange={update} placeholder="예: 시각디자인, 개발, 마케팅" />
                <TextField targetName="interestField" label="관심 분야" name="interestField" value={form.interestField} onChange={update} placeholder="예: F&B, 로컬 브랜드, 교육" />
                <TextField targetName="residenceRegion" label="거주 지역" name="residenceRegion" value={form.residenceRegion} onChange={update} placeholder="예: 부산 해운대구" />
                <TextField targetName="businessRegion" label="창업 희망 지역" name="businessRegion" value={form.businessRegion} onChange={update} placeholder="예: 부산, 서울, 온라인" />
                <TextField
                  targetName="initialBudget"
                  label="초기 예산"
                  name="initialBudget"
                  type="number"
                  min="0"
                  max="1000000000"
                  value={form.initialBudget}
                  onChange={update}
                  placeholder="예: 3000000"
                  wide
                />
              </div>
            </div>
          )}

          {stepIndex === 2 && (
            <div className="onboarding-step">
              <div className="onboarding-input-grid">
                <TextAreaField targetName="career" label="경험 또는 경력" name="career" value={form.career} onChange={update} placeholder="예: 카페 매니저 1년, SNS 채널 운영 경험" />
                <TextField targetName="strengthTags" label="강점 태그" name="strengthTags" value={form.strengthTags} onChange={update} placeholder="예: 실행력, 디자인 감각, SNS 운영" wide />
              </div>
            </div>
          )}

          {error && <div className="api-alert">{error}</div>}

          <div className="onboarding-bottom-bar">
            {stepIndex > 0 && (
              <button type="button" className="onboarding-secondary" onClick={moveBack} disabled={saving}>
                이전
              </button>
            )}
            <button className="onboarding-primary" disabled={saving || !canContinue}>
              {saving ? '저장 중...' : isLastStep ? '프로필 저장하고 시작하기' : '다음'} <Icon name="arrow" size={18} />
            </button>
          </div>
        </form>
      </section>
    </main>
  )
}
