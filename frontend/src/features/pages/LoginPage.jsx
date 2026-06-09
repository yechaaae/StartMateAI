import { useState } from 'react'
import { BrandMark } from '../../shared/components/BrandMark'
import { Icon } from '../../shared/components/Icon'
import { authApi } from '../../shared/api/client'

export const LoginPage = ({ go, onLogin }) => {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')
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

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="brand-line"><BrandMark /><b>StartMate AI 로그인</b></div>
        <h1>다시 만나서 반가워요</h1>
        <p>창업 프로필과 AI 작업공간을 이어서 사용하려면 로그인해주세요.</p>

        <form className="auth-form" onSubmit={submit}>
          <label>
            이메일
            <input name="email" type="email" value={form.email} onChange={update} placeholder="startmate@example.com" required />
          </label>
          <label>
            비밀번호
            <input name="password" type="password" value={form.password} onChange={update} placeholder="비밀번호" required />
          </label>

          {error && <div className="api-alert">{error}</div>}

          <button className="auth-submit" disabled={submitting}>
            {submitting ? '확인 중...' : '로그인'} <Icon name="arrow" size={18} />
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
