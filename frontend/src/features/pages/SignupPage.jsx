import { useState } from 'react'
import { BrandMark } from '../../shared/components/BrandMark'
import { Icon } from '../../shared/components/Icon'
import { authApi } from '../../shared/api/client'

const initialForm = {
  email: '',
  password: '',
  passwordConfirm: '',
  nickname: '',
}

export const SignupPage = ({ go, onSignup }) => {
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')

    if (form.password !== form.passwordConfirm) {
      setError('비밀번호와 비밀번호 확인이 일치하지 않습니다.')
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

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="brand-line"><BrandMark /><b>StartMate AI 회원가입</b></div>
        <h1>창업 작업공간을 만들어볼까요?</h1>
        <p>간단한 계정 정보만 입력하면 바로 창업 프로필 온보딩으로 이어집니다.</p>

        <form className="auth-form" onSubmit={submit}>
          <label>
            이메일
            <input name="email" type="email" value={form.email} onChange={update} placeholder="startmate@example.com" required />
          </label>
          <label>
            닉네임
            <input name="nickname" value={form.nickname} onChange={update} placeholder="민서" required />
          </label>
          <label>
            비밀번호
            <input name="password" type="password" value={form.password} onChange={update} placeholder="비밀번호" required />
          </label>
          <label>
            비밀번호 확인
            <input name="passwordConfirm" type="password" value={form.passwordConfirm} onChange={update} placeholder="비밀번호를 한 번 더 입력" required />
          </label>

          {error && <div className="api-alert">{error}</div>}

          <button className="auth-submit" disabled={submitting}>
            {submitting ? '가입 중...' : '회원가입'} <Icon name="arrow" size={18} />
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
