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

const initialForm = {
  email: '',
  password: '',
  passwordConfirm: '',
  nickname: '',
}

const signupFields = [
  {
    name: 'email',
    label: '이메일',
    type: 'email',
    placeholder: 'startmate@example.com',
    autoComplete: 'email',
  },
  {
    name: 'nickname',
    label: '닉네임',
    type: 'text',
    placeholder: '민서',
    autoComplete: 'nickname',
  },
  {
    name: 'password',
    label: '비밀번호',
    type: 'password',
    placeholder: '6자 이상',
    autoComplete: 'new-password',
  },
  {
    name: 'passwordConfirm',
    label: '비밀번호 확인',
    type: 'password',
    placeholder: '비밀번호를 한 번 더 입력',
    autoComplete: 'new-password',
    revealWithPrevious: true,
  },
]

export const SignupPage = ({ go, onSignup }) => {
  const [form, setForm] = useState(initialForm)
  const [revealedCount, setRevealedCount] = useState(1)
  const [focusTarget, setFocusTarget] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const fieldRefs = useRef({})
  const visibleFieldNames = getVisibleAuthFieldNames(signupFields, revealedCount)
  const passwordsMatch = form.password === form.passwordConfirm
  const canSubmit = signupFields.every((field) => isAuthStepValueReady(field.name, form[field.name]))
    && passwordsMatch
  const allFieldsVisible = revealedCount >= signupFields.length
  const canPressPrimary = allFieldsVisible
    ? canSubmit
    : canRevealNextAuthField(signupFields, revealedCount, form)

  const revealNextField = () => {
    const nextCount = getNextAuthRevealCount(signupFields, revealedCount, form)

    if (nextCount > revealedCount) {
      setFocusTarget(signupFields[revealedCount].name)
      setRevealedCount(nextCount)
    }
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

    if (!passwordsMatch) {
      setError('비밀번호와 비밀번호 확인이 일치하지 않습니다.')
      return
    }

    if (!canSubmit) {
      return
    }

    setSubmitting(true)
    try {
      const user = await authApi.signup(form)
      await onSignup(user)
    } catch (signupError) {
      setError(signupError.message)
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => {
    if (focusTarget) {
      fieldRefs.current[focusTarget]?.focus()
    }
  }, [focusTarget])

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <button type="button" className="auth-brand-link" onClick={() => go('landing')}>
          <BrandMark /><b>StartMate AI</b>
        </button>
        <h1>창업 작업공간을 만들어볼까요?</h1>
        <p>필요한 정보가 준비되는 순서대로 아래 입력칸이 펼쳐집니다.</p>

        <form className="auth-form auth-form-expand" onSubmit={submit}>
          {signupFields.map((field) => {
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
                    ref={(element) => {
                      fieldRefs.current[field.name] = element
                    }}
                    name={field.name}
                    type={field.type}
                    value={form[field.name]}
                    onChange={update}
                    onBlur={completeField}
                    onKeyDown={completeField}
                    placeholder={field.placeholder}
                    autoComplete={field.autoComplete}
                    required
                  />
                </span>
              </label>
            )
          })}

          {error && <div className="api-alert">{error}</div>}

          <button className="auth-submit" disabled={submitting || !canPressPrimary}>
            {submitting ? '가입 중...' : allFieldsVisible ? '회원가입' : '다음'} <Icon name="arrow" size={18} />
          </button>
        </form>

        <div className="auth-switch">
          <span>이미 계정이 있나요?</span>
          <button type="button" onClick={() => go('login')}>로그인</button>
        </div>
      </section>
    </main>
  )
}
