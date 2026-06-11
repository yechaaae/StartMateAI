import { useEffect, useRef, useState } from 'react'
import { BrandMark } from '../../shared/components/BrandMark'
import { Icon } from '../../shared/components/Icon'
import { authApi } from '../../shared/api/client'
import {
  canRevealNextAuthField,
  getNextAuthRevealCount,
  getVisibleAuthFieldNames,
  isAuthStepValueReady,
} from './authStepFlow'
import { loginFields } from './authFormFields'

export const LoginPage = ({ go, onLogin }) => {
  const [form, setForm] = useState({ email: '', password: '' })
  const [revealedCount, setRevealedCount] = useState(1)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const passwordRef = useRef(null)
  const visibleFieldNames = getVisibleAuthFieldNames(loginFields, revealedCount)
  const canSubmit = loginFields.every((field) => isAuthStepValueReady(field.name, form[field.name]))
  const showPassword = visibleFieldNames.includes('password')
  const allFieldsVisible = revealedCount >= loginFields.length
  const canPressPrimary = allFieldsVisible
    ? canSubmit
    : canRevealNextAuthField(loginFields, revealedCount, form)

  const revealNextField = () => {
    setRevealedCount((current) => getNextAuthRevealCount(loginFields, current, form))
  }

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
    setError('')
  }

  const completeField = (event) => {
    if (event.type === 'keydown' && event.key !== 'Enter') {
      return
    }

    if (event.type === 'keydown') {
      event.preventDefault()
    }

    revealNextField()
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')

    if (!allFieldsVisible) {
      revealNextField()
      return
    }

    if (!canSubmit) {
      return
    }

    setSubmitting(true)

    try {
      const user = await authApi.login(form)
      await onLogin(user)
    } catch (loginError) {
      setError(loginError.message)
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => {
    if (showPassword && !form.password) {
      passwordRef.current?.focus()
    }
  }, [form.password, showPassword])

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <button type="button" className="auth-brand-link" onClick={() => go('landing')}>
          <BrandMark /><b>StartMate AI</b>
        </button>
        <h1>다시 만나서 반가워요</h1>
        <p>이메일을 입력하면 비밀번호 입력창이 자연스럽게 이어집니다.</p>

        <form
          className="auth-form auth-form-expand"
          onSubmit={submit}
          autoComplete="off"
          data-form-type="other"
        >
          {loginFields.map((field) => {
            if (!visibleFieldNames.includes(field.name)) {
              return null
            }

            return (
              <label
                className="auth-reveal-field"
                key={field.name}
                style={{ '--reveal-index': visibleFieldNames.indexOf(field.name) }}
              >
                <span className="auth-reveal-inner">
                  <span>{field.label}</span>
                  <input
                    ref={field.name === 'password' ? passwordRef : undefined}
                    name={field.name}
                    type={field.type}
                    value={form[field.name]}
                    onChange={update}
                    onBlur={completeField}
                    onKeyDown={completeField}
                    placeholder={field.placeholder}
                    autoComplete={field.autoComplete}
                    data-lpignore={field.ignorePasswordManagers ? 'true' : undefined}
                    data-1p-ignore={field.ignorePasswordManagers ? 'true' : undefined}
                    data-form-type={field.ignorePasswordManagers ? 'other' : undefined}
                    required
                  />
                </span>
              </label>
            )
          })}

          {error && <div className="api-alert">{error}</div>}

          <button className="auth-submit" disabled={submitting || !canPressPrimary}>
            {submitting ? '확인 중...' : allFieldsVisible ? '로그인' : '다음'} <Icon name="arrow" size={18} />
          </button>
        </form>

        <div className="auth-switch">
          <span>아직 계정이 없나요?</span>
          <button type="button" onClick={() => go('signup')}>회원가입</button>
        </div>
      </section>
    </main>
  )
}
