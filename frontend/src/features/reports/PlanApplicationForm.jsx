import { useEffect, useMemo, useState } from 'react'

// AI가 생성한 섹션([제목, 본문])에서 특정 항목(aiSource 키워드)에 해당하는 답변을 찾는다.
const aiValueFromSections = (aiSource, sections) => {
  if (!aiSource) return ''
  const match = (sections ?? []).find(([title]) => String(title).includes(aiSource))
  return match ? String(match[1] ?? '') : ''
}

// 항목 초기값: AI 생성 답변 > 프로필 기반 기본값 > 빈 값.
const initialValues = (form, sections, defaults) => {
  const values = {}
  for (const field of form.fields) {
    const fallback = defaults?.[field.key] ?? ''
    if (field.type === 'checkboxGroup') {
      values[field.key] = field.defaultAll ? [...(field.options ?? [])] : []
    } else if (field.type === 'consent') {
      values[field.key] = true
    } else if (field.aiSource) {
      values[field.key] = aiValueFromSections(field.aiSource, sections) || fallback
    } else {
      values[field.key] = fallback
    }
  }
  return values
}

const serialize = (form, values) =>
  form.fields
    .map((field) => {
      const value = values[field.key]
      if (field.type === 'consent') return `${field.label}: ${value ? (field.consentText ?? '동의 함') : '미동의'}`
      if (field.type === 'checkboxGroup') return `${field.label}: ${(value ?? []).join(', ')}`
      return `${field.label}\n${value ?? ''}`
    })
    .join('\n\n')

export const PlanApplicationForm = ({ form, sections, defaults = null, loading = false }) => {
  const [values, setValues] = useState(() => initialValues(form, sections, defaults))
  const [copied, setCopied] = useState(false)
  const [aiTouchedKeys, setAiTouchedKeys] = useState({})

  // AI 생성 답변이 도착/변경되면 해당 칸을 채운다. 사용자가 직접 고친 칸은 덮어쓰지 않는다.
  const aiKey = useMemo(() => JSON.stringify(sections ?? []), [sections])
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setValues((prev) => {
      const next = { ...prev }
      for (const field of form.fields) {
        if (!field.aiSource) continue
        const aiValue = aiValueFromSections(field.aiSource, sections)
        if (aiValue && !aiTouchedKeys[field.key]) {
          next[field.key] = aiValue
        }
      }
      return next
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aiKey])

  const setField = (key, value) => {
    setAiTouchedKeys((prev) => ({ ...prev, [key]: true }))
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  const toggleInGroup = (key, option) => {
    setValues((prev) => {
      const current = prev[key] ?? []
      const nextGroup = current.includes(option)
        ? current.filter((item) => item !== option)
        : [...current, option]
      return { ...prev, [key]: nextGroup }
    })
  }

  const copyAll = async () => {
    try {
      await navigator.clipboard?.writeText(serialize(form, values))
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      /* 클립보드 실패는 무시 */
    }
  }

  return (
    <div className="plan-appform">
      {form.analysis && (
        <section className="plan-analysis">
          <h3 className="plan-analysis-title">{form.analysis.title}</h3>
          {form.analysis.sections.map(([title, body]) => (
            <div className="plan-analysis-row" key={title}>
              <h4>{title}</h4>
              <p>{body}</p>
            </div>
          ))}
        </section>
      )}

      <div className="plan-appform-head">
        <h3>{form.title}</h3>
        {form.description && <p>{form.description}</p>}
      </div>

      {form.fields.map((field) => (
        <div className="plan-appform-field" key={field.key}>
          <label className="plan-appform-label">
            {field.label}
            {field.required && <span className="plan-appform-req"> *</span>}
            {field.aiSource && (
              <span className="plan-appform-ai">{loading ? 'AI 작성 중…' : 'AI 작성'}</span>
            )}
          </label>

          {field.type === 'text' && (
            <input
              className="plan-appform-input"
              value={values[field.key] ?? ''}
              placeholder={field.placeholder ?? ''}
              onChange={(event) => setField(field.key, event.target.value)}
            />
          )}

          {field.type === 'textarea' && (
            <textarea
              className="plan-appform-textarea"
              rows={5}
              value={values[field.key] ?? ''}
              placeholder={loading ? 'AI가 답변을 작성하고 있어요…' : field.placeholder ?? ''}
              onChange={(event) => setField(field.key, event.target.value)}
            />
          )}

          {field.type === 'radio' && (
            <div className="plan-appform-options">
              {field.options.map((option) => (
                <label key={option} className="plan-appform-choice">
                  <input
                    type="radio"
                    name={field.key}
                    checked={values[field.key] === option}
                    onChange={() => setField(field.key, option)}
                  />
                  {option}
                </label>
              ))}
            </div>
          )}

          {field.type === 'checkboxGroup' && (
            <div className="plan-appform-options">
              {field.options.map((option) => (
                <label key={option} className="plan-appform-choice">
                  <input
                    type="checkbox"
                    checked={(values[field.key] ?? []).includes(option)}
                    onChange={() => toggleInGroup(field.key, option)}
                  />
                  {option}
                </label>
              ))}
            </div>
          )}

          {field.type === 'consent' && (
            <label className="plan-appform-choice">
              <input
                type="checkbox"
                checked={Boolean(values[field.key])}
                onChange={(event) => setField(field.key, event.target.checked)}
              />
              {field.consentText ?? '동의 함'}
            </label>
          )}
        </div>
      ))}

      <div className="plan-appform-actions">
        <button type="button" className="om-primary" onClick={copyAll}>
          {copied ? '복사됨!' : '작성 내용 복사'}
        </button>
      </div>
    </div>
  )
}
