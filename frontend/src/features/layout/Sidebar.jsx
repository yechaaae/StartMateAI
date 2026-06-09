import { useState } from 'react'
import { features, featureOrder } from '../../shared/data/features'
import { profile } from '../../shared/data/profile'
import { workspaces } from '../../shared/data/workspaces'
import { Icon } from '../../shared/components/Icon'

export const Sidebar = ({ route, go, workspace, setWorkspace }) => {
  const [open, setOpen] = useState(false)
  return (
    <aside className="sidebar">
      <div className="workspace-switch">
        <button className="workspace-button" onClick={() => setOpen((v) => !v)}>
          <span>{workspace.emoji}</span>
          <b>{workspace.name}</b>
          <small>StartMate AI</small>
        </button>
        {open && (
          <div className="workspace-menu">
            {workspaces.map((ws) => (
              <button key={ws.id} onClick={() => { setWorkspace(ws); setOpen(false); go('home') }}>
                <span>{ws.emoji}</span>
                <b>{ws.name}</b>
                <small>{ws.desc}</small>
              </button>
            ))}
          </div>
        )}
      </div>

      <button className={route === 'discuss' ? 'discuss-btn on' : 'discuss-btn'} onClick={() => go('discuss')}>
        <Icon name="discuss" size={18} /> AI와 토론하기
      </button>

      <nav>
        <p>워크스페이스</p>
        <button className={route === 'home' ? 'on' : ''} onClick={() => go('home')}><Icon name="home" />워크스페이스</button>
        <p>AI 기능</p>
        {featureOrder.map((id) => {
          const feature = features[id]
          return <button key={id} className={route === id ? 'on' : ''} onClick={() => go(id)}><Icon name={feature.icon} />{feature.title}</button>
        })}
        <p>보관함</p>
        <button className={route === 'saved' ? 'on' : ''} onClick={() => go('saved')}><Icon name="bookmark" />저장한 결과</button>
      </nav>
      <div className="user-box">
        <span>{profile.name.slice(0, 1)}</span>
        <b>{profile.name}</b>
        <small>{profile.role} · {profile.loc}</small>
      </div>
    </aside>
  )
}
