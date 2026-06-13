import { useEffect, useRef, useState } from 'react'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { StartMateLogo } from '../../shared/components/StartMateLogo'
import { Icon } from '../../shared/components/Icon'
import { startupProfileApi } from '../../shared/api/client'
import {
  getFirstIncompleteOnboardingField,
  getOnboardingProgress,
  getOnboardingStepCount,
  getOnboardingSteps,
  getVisibleOnboardingFields,
  isOnboardingStepComplete,
} from './onboardingFlow'
import { AddressField, BudgetField, TagField } from './onboardingFields'

const stageOptions = [
  ['PRE_STARTUP', '창업 전', '아직 시작 전이에요. 아이템부터 정리하고 싶어요'],
  ['POST_STARTUP', '창업 후', '이미 운영 중이에요. 지금 사업을 도와주세요'],
]

const teamStatusOptions = [
  ['SOLO', '개인', '혼자 빠르게 검증하고 있어요'],
  ['HAS_TEAM', '팀 있음', '함께 실행할 멤버가 있어요'],
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

const operatingPeriodOptions = [
  ['UNDER_6M', '6개월 미만', '이제 막 시작했어요'],
  ['SIX_TO_12M', '6개월~1년', '자리를 잡아가는 중이에요'],
  ['ONE_TO_3Y', '1~3년', '어느 정도 운영해봤어요'],
  ['OVER_3Y', '3년 이상', '오래 운영하고 있어요'],
]

const initialForm = {
  stage: '',
  major: '',
  career: '',
  interestField: '',
  residenceRegion: '',
  businessRegion: '',
  initialBudget: '',
  teamStatus: '',
  preferredBusinessType: '',
  strengthTags: '',
  currentItemName: '',
  currentIndustry: '',
  operatingPeriod: '',
}

// 기존에 저장된 프로필(원 단위 예산 등)을 온보딩 폼 형태로 변환합니다.
const profileToForm = (profile) => ({
  stage: profile.stage ?? '',
  major: profile.major ?? '',
  career: profile.career ?? '',
  interestField: profile.interestField ?? '',
  residenceRegion: profile.residenceRegion ?? '',
  businessRegion: profile.businessRegion ?? '',
  initialBudget: profile.initialBudget ? String(Math.round(profile.initialBudget / 10000)) : '',
  teamStatus: profile.teamStatus ?? '',
  preferredBusinessType: profile.preferredBusinessType ?? '',
  strengthTags: profile.strengthTags ?? '',
  currentItemName: profile.currentItemName ?? '',
  currentIndustry: profile.currentIndustry ?? '',
  operatingPeriod: profile.operatingPeriod ?? '',
})

const stageStepCopy = {
  title: '먼저, 지금 어느 단계에 계신가요?',
  description: '창업 전인지 이미 사업을 운영 중인지에 따라 맞춤 질문을 준비할게요.',
}

const preStepCopy = [
  {
    title: '어떤 창업을 꿈꾸고 계신가요?',
    description: '맞춤 추천을 위해 선호 창업 형태와 팀 구성을 먼저 볼게요.',
  },
  {
    title: '아이디어의 기본 조건을 알려주세요',
    description: '분야, 지역, 예산을 바탕으로 현실적인 추천을 좁혀갑니다.',
  },
  {
    title: '나만의 경험과 강점을 더해주세요',
    description: '경험과 강점은 사업 아이디어와 지원사업 매칭 품질을 높여줍니다.',
  },
]

const postStepCopy = [
  {
    title: '지금 운영 중인 사업을 알려주세요',
    description: '현재 아이템과 업종, 위치, 운영 기간을 바탕으로 운영을 도와드릴게요.',
  },
  {
    title: '사업 형태와 팀 구성은 어떤가요?',
    description: '현재 운영 형태와 팀 상황을 확인할게요.',
  },
  {
    title: '대표님의 배경을 알려주세요',
    description: '전공·관심 분야·거주 지역은 추천 품질을 높여줍니다.',
  },
  {
    title: '경험과 강점을 더해주세요',
    description: '경험과 강점은 운영·마케팅 제안 품질을 높여줍니다.',
  },
]

const buildStepCopy = (stage) => {
  const rest = stage === 'POST_STARTUP' ? postStepCopy : stage === 'PRE_STARTUP' ? preStepCopy : []
  return [stageStepCopy, ...rest].map((copy, index) => ({ ...copy, eyebrow: `${index + 1}단계` }))
}

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

const OptionSection = ({ targetName, title, options, value, onSelect, reveal = false, columns }) => (
  <div
    className={reveal ? 'onboarding-section reveal-section' : 'onboarding-section'}
    data-onboarding-target={targetName}
  >
    <h2>{title}</h2>
    <div className={columns === 2 ? 'onboarding-option-grid two-col' : 'onboarding-option-grid'}>
      {options.map(([optionValue, optionTitle, optionDescription]) => (
        <OptionCard
          key={optionValue}
          selected={value === optionValue}
          title={optionTitle}
          description={optionDescription}
          onClick={() => onSelect(optionValue)}
        />
      ))}
    </div>
  </div>
)

export const Onboarding = ({ onComplete }) => {
  const [form, setForm] = useState(initialForm)
  const [stepIndex, setStepIndex] = useState(0)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const flowRef = useRef(null)

  const stage = form.stage
  const steps = getOnboardingSteps(stage)
  const stepCount = getOnboardingStepCount(stage)
  const currentStepFields = steps[stepIndex] ?? []
  const stepCopy = buildStepCopy(stage)
  const step = stepCopy[stepIndex] ?? stepCopy[0]
  const progress = getOnboardingProgress(stepIndex, stage)
  const isLastStep = stepIndex === stepCount - 1
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

    if (name === 'preferredBusinessType' && !form.teamStatus) {
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
      setStepIndex((current) => Math.min(current + 1, stepCount - 1))
      return
    }

    setSaving(true)

    try {
      const profile = await startupProfileApi.save({
        ...form,
        // 입력은 만원 단위, 저장은 원 단위로 변환합니다.
        initialBudget: stage === 'PRE_STARTUP' ? Math.round(Number(form.initialBudget) || 0) * 10000 : null,
      })
      setSaved(true)
      window.setTimeout(() => onComplete(profile), 700)
    } catch (profileError) {
      setError(profileError.message)
    } finally {
      setSaving(false)
    }
  }

  // Home에서 "수정"으로 다시 들어오면 기존에 저장한 프로필을 채워줍니다.
  // 최초 온보딩(프로필 없음)이면 404가 떨어지므로 빈 폼을 유지합니다.
  useEffect(() => {
    let active = true
    startupProfileApi.get()
      .then((profile) => {
        if (active && profile) {
          setForm((current) => ({ ...current, ...profileToForm(profile) }))
        }
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [])

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

  const renderStep = () => {
    if (currentStepFields.includes('stage')) {
      return (
        <div className="onboarding-step">
          <OptionSection
            targetName="stage"
            title="창업 단계"
            options={stageOptions}
            value={form.stage}
            onSelect={(value) => select('stage', value)}
            columns={2}
          />
        </div>
      )
    }

    if (currentStepFields.includes('currentItemName')) {
      return (
        <div className="onboarding-step">
          <div className="onboarding-input-grid">
            <TextField targetName="currentItemName" label="현재 아이템 / 사업명" name="currentItemName" value={form.currentItemName} onChange={update} placeholder="예: 구남로 수제 쿠키" />
            <TextField targetName="currentIndustry" label="업종" name="currentIndustry" value={form.currentIndustry} onChange={update} placeholder="예: 카페, 디저트, 음식점" />
            <AddressField targetName="businessRegion" label="사업장 위치" name="businessRegion" value={form.businessRegion} onChange={(next) => select('businessRegion', next)} placeholder="예: 부산 해운대구 (검색 또는 직접 입력)" />
          </div>
          <OptionSection
            targetName="operatingPeriod"
            title="운영 기간"
            options={operatingPeriodOptions}
            value={form.operatingPeriod}
            onSelect={(value) => select('operatingPeriod', value)}
          />
        </div>
      )
    }

    if (currentStepFields.includes('preferredBusinessType')) {
      return (
        <div className="onboarding-step">
          <OptionSection
            targetName="preferredBusinessType"
            title={stage === 'POST_STARTUP' ? '현재 사업 형태' : '선호 창업 형태'}
            options={businessTypeOptions}
            value={form.preferredBusinessType}
            onSelect={(value) => select('preferredBusinessType', value)}
            columns={2}
          />
          {visibleFields.includes('teamStatus') && (
            <OptionSection
              targetName="teamStatus"
              title="팀 구성"
              options={teamStatusOptions}
              value={form.teamStatus}
              onSelect={(value) => select('teamStatus', value)}
              reveal
            />
          )}
        </div>
      )
    }

    if (currentStepFields.includes('career')) {
      return (
        <div className="onboarding-step">
          <div className="onboarding-input-grid">
            <TextAreaField targetName="career" label="경험 또는 경력" name="career" value={form.career} onChange={update} placeholder="예: 카페 매니저 1년, SNS 채널 운영 경험" />
            <TagField targetName="strengthTags" label="강점 태그" name="strengthTags" value={form.strengthTags} onChange={(next) => select('strengthTags', next)} placeholder="예: 실행력 (엔터로 추가)" max={10} />
          </div>
        </div>
      )
    }

    // 공통 기본 정보 (창업 전: 지역/예산 포함, 창업 후: 전공·관심·거주만)
    return (
      <div className="onboarding-step">
        <div className="onboarding-input-grid">
          <TagField targetName="major" label="전공 또는 보유 역량" name="major" value={form.major} onChange={(next) => select('major', next)} placeholder="예: 시각디자인 (엔터로 추가)" max={10} />
          <TagField targetName="interestField" label="관심 분야" name="interestField" value={form.interestField} onChange={(next) => select('interestField', next)} placeholder="예: F&B (엔터로 추가)" max={10} />
          <AddressField targetName="residenceRegion" label="거주 지역" name="residenceRegion" value={form.residenceRegion} onChange={(next) => select('residenceRegion', next)} placeholder="예: 부산 해운대구 (검색 또는 직접 입력)" />
          {currentStepFields.includes('businessRegion') && (
            <AddressField targetName="businessRegion" label="창업 희망 지역" name="businessRegion" value={form.businessRegion} onChange={(next) => select('businessRegion', next)} placeholder="예: 부산 해운대구 (검색 또는 직접 입력)" />
          )}
          {currentStepFields.includes('initialBudget') && (
            <BudgetField targetName="initialBudget" label="초기 예산" name="initialBudget" value={form.initialBudget} onChange={(next) => select('initialBudget', next)} />
          )}
        </div>
      </div>
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
          <StartMateLogo /><b>StartMate AI</b>
        </button>

        <div className="onboarding-step-indicator">
          <span className="onboarding-step-eyebrow">{step.eyebrow}</span>
          <span className="onboarding-step-count">{progress.current} / {progress.total}</span>
        </div>

        <div className="onboarding-progress">
          <span style={{ width: `${progress.percent}%` }} />
        </div>

        <header className="onboarding-flow-head">
          <h1>{step.title}</h1>
          <p>{step.description}</p>
        </header>

        <form className="onboarding-flow-form" onSubmit={submit}>
          {renderStep()}

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
