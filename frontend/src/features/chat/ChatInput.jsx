import { useState } from 'react'
import { Icon } from '../../shared/components/Icon'

export const ChatInput = ({ onSend, disabled, placeholder, suggestions = [], accent = 'var(--brand)' }) => {
  const [value, setValue] = useState('')
  const submit = (text = value) => {
    const next = text.trim()
    if (!next || disabled) return
    setValue('')
    onSend(next)
  }
  return (
    <div className="chat-input">
      {!!suggestions.length && <div className="suggestions">{suggestions.map((s) => <button key={s} onClick={() => submit(s)} disabled={disabled}>{s}</button>)}</div>}
      <div className="input-shell">
        <textarea value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }} placeholder={placeholder} rows={1} />
        <button style={{ background: value.trim() && !disabled ? accent : '#dfe2ea' }} onClick={() => submit()} disabled={!value.trim() || disabled}>
          <Icon name={disabled ? 'clock' : 'send'} size={18} />
        </button>
      </div>
    </div>
  )
}
