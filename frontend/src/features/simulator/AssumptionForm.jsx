import { useState } from 'react'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

const formatWon = (value) => Number(value || 0).toLocaleString('ko-KR')
const parseNumber = (value) => Number(String(value).replace(/[^\d.]/g, '')) || 0

const costPresets = {
  lean: {
    label: '작게 시작',
    description: '혼자 운영하고 홍보비를 아끼는 경우',
    laborCost: 800000,
    marketingCost: 200000,
    otherFixedCost: 300000,
    variableCostRate: 0.32,
  },
  normal: {
    label: '보통',
    description: '기본 인건비와 홍보비를 반영한 경우',
    laborCost: 1500000,
    marketingCost: 500000,
    otherFixedCost: 500000,
    variableCostRate: 0.35,
  },
  active: {
    label: '공격적으로',
    description: '초기 홍보와 운영비를 넉넉히 잡은 경우',
    laborCost: 2200000,
    marketingCost: 900000,
    otherFixedCost: 800000,
    variableCostRate: 0.4,
  },
}

const MoneyField = ({ label, name, value, onChange, suffix = '원' }) => (
  <label className="sim-field">
    <span>{label}</span>
    <div>
      <input
        inputMode="numeric"
        name={name}
        value={formatWon(value)}
        onChange={(event) => onChange(name, parseNumber(event.target.value))}
      />
      {suffix && <em>{suffix}</em>}
    </div>
  </label>
)

const NumberField = ({ label, name, value, onChange, suffix }) => (
  <label className="sim-field">
    <span>{label}</span>
    <div>
      <input
        type="number"
        name={name}
        value={value}
        onChange={(event) => onChange(name, Number(event.target.value))}
      />
      {suffix && <em>{suffix}</em>}
    </div>
  </label>
)

export const AssumptionForm = ({ location, idea, onBack, onRun }) => {
  const [preset, setPreset] = useState('normal')
  const [form, setForm] = useState({
    initialBudget: 10000000,
    pricePerOrder: 15000,
    expectedDailyOrders: 35,
    operatingDays: 24,
    monthlyRent: location?.rent || 2000000,
    ...costPresets.normal,
  })

  const updateValue = (name, value) => {
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const applyPreset = (key) => {
    setPreset(key)
    setForm((prev) => ({ ...prev, ...costPresets[key] }))
  }

  const revenue = form.pricePerOrder * form.expectedDailyOrders * form.operatingDays
  const variableCost = Math.round(revenue * form.variableCostRate)
  const fixedCost = form.monthlyRent + form.laborCost + form.marketingCost + form.otherFixedCost
  const profit = revenue - variableCost - fixedCost
  const breakEvenCount = Math.ceil(fixedCost / Math.max(1, form.pricePerOrder * (1 - form.variableCostRate)))

  return (
    <section className="sim-step-panel step-in">
      <Card className="sim-location-summary">
        <div className="sim-location-icon"><Icon name="pin" size={20} /></div>
        <div>
          <b>{location?.address || '선택한 위치'}</b>
          <span>대략 월세 {formatWon(form.monthlyRent)}원 · {idea?.title || '선택한 아이템'}으로 가볍게 보기</span>
        </div>
        <button onClick={onBack}>위치 다시 선택</button>
      </Card>

      <div className="sim-form-layout light">
        <Card className="sim-assumption-card">
          <div className="sim-section-copy compact">
            <h2>간단히 가정하기</h2>
            <p>정확한 사업계획서가 아니라, 이 아이템을 이 지역에서 해보면 어느 정도 나올지 빠르게 보는 단계예요.</p>
          </div>

          <div className="sim-preset-row">
            {Object.entries(costPresets).map(([key, option]) => (
              <button
                key={key}
                type="button"
                className={preset === key ? 'active' : ''}
                onClick={() => applyPreset(key)}
              >
                <b>{option.label}</b>
                <span>{option.description}</span>
              </button>
            ))}
          </div>

          <div className="sim-field-grid compact">
            <MoneyField label="건당 금액" name="pricePerOrder" value={form.pricePerOrder} onChange={updateValue} />
            <NumberField label="하루 판매/이용 건수" name="expectedDailyOrders" value={form.expectedDailyOrders} onChange={updateValue} suffix="건" />
            <NumberField label="월 운영일" name="operatingDays" value={form.operatingDays} onChange={updateValue} suffix="일" />
            <MoneyField label="예상 월세" name="monthlyRent" value={form.monthlyRent} onChange={updateValue} />
          </div>

          <details className="sim-advanced-box">
            <summary>조금 더 자세히 조정하기</summary>
            <div className="sim-field-grid compact">
              <MoneyField label="초기 여유자금" name="initialBudget" value={form.initialBudget} onChange={updateValue} />
              <MoneyField label="인건비" name="laborCost" value={form.laborCost} onChange={updateValue} />
              <MoneyField label="홍보비" name="marketingCost" value={form.marketingCost} onChange={updateValue} />
              <MoneyField label="기타 고정비" name="otherFixedCost" value={form.otherFixedCost} onChange={updateValue} />
            </div>
            <label className="sim-range-field">
              <div>
                <span>재료비/수수료 비율</span>
                <b>{Math.round(form.variableCostRate * 100)}%</b>
              </div>
              <input
                type="range"
                min="0.1"
                max="0.8"
                step="0.05"
                value={form.variableCostRate}
                onChange={(event) => updateValue('variableCostRate', Number(event.target.value))}
              />
            </label>
          </details>
        </Card>

        <Card className="sim-preview-card light">
          <span className="sim-preview-kicker">대략 보기</span>
          <h3>한 달에 이 정도 예상돼요</h3>
          <div className="sim-preview-list">
            <div><span>월 매출</span><b>{formatWon(revenue)}원</b></div>
            <div><span>월 비용</span><b className="warn">{formatWon(variableCost + fixedCost)}원</b></div>
            <div className="total"><span>남는 돈</span><b className={profit >= 0 ? 'good' : 'bad'}>{formatWon(profit)}원</b></div>
          </div>
          <div className="sim-break-even">
            <span>손익분기 건수</span>
            <strong>{breakEvenCount}건</strong>
          </div>
          <button className="sim-primary-btn wide" onClick={() => onRun(form)}>
            30일 흐름 보기 <Icon name="arrow" size={17} />
          </button>
          <p className="sim-light-note">실제 창업 판단용 확정 수치가 아니라, 아이템과 지역을 비교하기 위한 빠른 추정치입니다.</p>
        </Card>
      </div>
    </section>
  )
}
