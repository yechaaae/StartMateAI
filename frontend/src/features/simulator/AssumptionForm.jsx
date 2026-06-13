import { useState } from 'react'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'
import { buildMonthlyPreview } from './simulationCalculations'

const formatWon = (value) => Number(value || 0).toLocaleString('ko-KR')

// LLM 시나리오를 받기 전 잠깐 보여줄 기본값(편집 불가).
const DEFAULT_FORM = {
  initialBudget: 10000000,
  pricePerOrder: 15000,
  expectedDailyOrders: 35,
  operatingDays: 24,
  monthlyRent: 2000000,
  laborCost: 1500000,
  marketingCost: 500000,
  otherFixedCost: 500000,
  variableCostRate: 0.35,
}

const ReadonlyField = ({ label, value }) => (
  <div className="sim-readonly-field">
    <span>{label}</span>
    <b>{value}</b>
  </div>
)

const scenarioKey = (scenario) => scenario?.key ?? scenario?.label

// 가정값은 AI(파이낸스 에이전트)가 3가지 시나리오로 제안한다.
// 사용자는 값을 직접 입력하지 않고, 시나리오 하나를 골라 확인만 한다.
export const AssumptionForm = ({ location, idea, onBack, onRun, suggested, loading }) => {
  const scenarios = Array.isArray(suggested?.scenarios) ? suggested.scenarios : []
  const [selectedKey, setSelectedKey] = useState(null)
  const fallbackIndex = Math.min(1, scenarios.length - 1)
  const defaultScenario = scenarios.find((scenario) => scenario.key === 'normal') ?? scenarios[fallbackIndex]
  const selectedScenario = scenarios.find((scenario) => scenarioKey(scenario) === selectedKey) ?? defaultScenario
  const selectedScenarioKey = scenarioKey(selectedScenario)
  const form = {
    ...DEFAULT_FORM,
    monthlyRent: location?.rent || DEFAULT_FORM.monthlyRent,
    ...selectedScenario,
  }

  const selectScenario = (scenario) => {
    setSelectedKey(scenarioKey(scenario))
  }

  const preview = buildMonthlyPreview(form)

  return (
    <section className="sim-step-panel step-in">
      <Card className="sim-location-summary">
        <div className="sim-location-icon"><Icon name="pin" size={20} /></div>
        <div>
          <b>{location?.address || '선택한 위치'}</b>
          <span>대략 월세 {formatWon(form.monthlyRent)}원 · {idea?.title || '선택한 아이템'}으로 가볍게 보기</span>
        </div>
        <button type="button" onClick={onBack}>위치 다시 선택</button>
      </Card>

      <div className="sim-form-layout light">
        <Card className="sim-assumption-card">
          <div className="sim-section-copy compact">
            <h2>간단히 가정하기</h2>
            <p>AI가 이 아이템·지역에 맞춰 3가지 가정을 제안했어요. 하나를 골라 첫 30일 흐름을 추정합니다.</p>
          </div>

          {loading && (
            <>
              <div className="sim-ai-assumption-note loading">
                <Icon name="sparkle" size={14} /> AI가 이 아이템·위치에 맞는 가정값을 계산하고 있어요…
              </div>
              <div className="sim-loading-spin">
                <span className="sim-spinner" aria-hidden="true" />
              </div>
            </>
          )}

          {!loading && (
            <>
              {scenarios.length > 0 && (
                <div className="sim-preset-row">
                  {scenarios.map((scenario) => (
                    <button
                      key={scenarioKey(scenario)}
                      type="button"
                      className={selectedScenarioKey === scenarioKey(scenario) ? 'active' : ''}
                      onClick={() => selectScenario(scenario)}
                    >
                      <b>{scenario.label}</b>
                      <span>{scenario.description}</span>
                    </button>
                  ))}
                </div>
              )}

              <div className="sim-readonly-grid compact">
                <ReadonlyField label="건당 금액" value={`${formatWon(form.pricePerOrder)}원`} />
                <ReadonlyField label="하루 판매/이용 건수" value={`${formatWon(form.expectedDailyOrders)}건`} />
                <ReadonlyField label="월 운영일" value={`${formatWon(form.operatingDays)}일`} />
                <ReadonlyField label="예상 월세" value={`${formatWon(form.monthlyRent)}원`} />
              </div>

              <details className="sim-advanced-box">
                <summary>자세히 보기</summary>
                <div className="sim-readonly-grid compact">
                  <ReadonlyField label="초기 여유자금" value={`${formatWon(form.initialBudget)}원`} />
                  <ReadonlyField label="인건비" value={`${formatWon(form.laborCost)}원`} />
                  <ReadonlyField label="홍보비" value={`${formatWon(form.marketingCost)}원`} />
                  <ReadonlyField label="기타 고정비" value={`${formatWon(form.otherFixedCost)}원`} />
                  <ReadonlyField label="재료비/수수료 비율" value={`${Math.round(form.variableCostRate * 100)}%`} />
                </div>
              </details>
            </>
          )}
        </Card>

        <Card className="sim-preview-card light">
          <span className="sim-preview-kicker">대략 보기</span>
          <h3>한 달에 이 정도 예상돼요</h3>
          <div className="sim-preview-list">
            <div><span>월 매출</span><b>{formatWon(preview.revenue)}원</b></div>
            <div><span>월 비용</span><b className="warn">{formatWon(preview.totalCost)}원</b></div>
            <div className="total"><span>남는 돈</span><b className={preview.profit >= 0 ? 'good' : 'bad'}>{formatWon(preview.profit)}원</b></div>
          </div>
          <div className="sim-break-even">
            <span>손익분기 건수</span>
            <strong>{preview.breakEvenCount}건</strong>
          </div>
          <button className="sim-primary-btn wide" onClick={() => onRun(form)} disabled={loading}>
            {loading ? '가정값 준비 중…' : <>30일 흐름 보기 <Icon name="arrow" size={17} /></>}
          </button>
          <p className="sim-light-note">실제 창업 판단용 확정 수치가 아니라, 아이템과 지역을 비교하기 위한 빠른 추정치입니다.</p>
        </Card>
      </div>

      <div className="sim-actions">
        <button type="button" className="sim-secondary-btn" onClick={onBack}>
          <Icon name="arrow" size={16} /> 위치 다시 선택
        </button>
      </div>
    </section>
  )
}
