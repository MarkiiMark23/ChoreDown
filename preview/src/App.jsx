import { useState } from 'react'
import { kids, tasks, rewards, redemptions, behaviors, transactions, APP_NAME, APP_ICON } from './mockData'
import './styles.css'

// ── Helpers ───────────────────────────────────────────────────────────────────
const Avatar = ({ name, color, size = 40 }) => (
  <div className="avatar" style={{ background: color, width: size, height: size, fontSize: size * 0.38 }}>
    {(name || '?')[0].toUpperCase()}
  </div>
)
const Badge = ({ children, variant = 'grey' }) => <span className={`badge badge-${variant}`}>{children}</span>
const Btn = ({ children, variant = 'primary', full, sm, onClick, style }) => (
  <button className={`btn btn-${variant}${full ? ' btn-full' : ''}${sm ? ' btn-sm' : ''}`} onClick={onClick} style={style}>
    {children}
  </button>
)
const catEmoji = c => ({ chores: '🧹', homework: '📚', hygiene: '🛁', outdoor: '🌳' }[c] || '✅')
const priorityColor = p => ({ 4: '#F44336', 3: '#FF9800', 2: '#6C63FF', 1: '#4CAF50' }[p])
const txIcon = t => ({ task: '📋', behavior_positive: '⭐', behavior_negative: '⚠️', redemption: '🎁', bonus: '🎉' }[t] || '⚡')

// ── Landing ───────────────────────────────────────────────────────────────────
function Landing({ onEnter }) {
  return (
    <div className="landing">
      <div className="landing-hero">
        <div className="landing-logo">{APP_ICON}</div>
        <h1 className="landing-title">{APP_NAME}</h1>
        <p className="landing-sub">Tasks for kids. Rewards they'll love. Peace of mind for parents.</p>
        <div className="landing-btns">
          <Btn onClick={() => onEnter('parent')}>👨‍👩‍👧 Parent View</Btn>
          <Btn variant="outline" onClick={() => onEnter('kid')}>🧒 Kid View</Btn>
        </div>
      </div>
      <div className="features">
        {[['📋','Assign Tasks','Give kids clear tasks with due dates and point values'],
          ['⭐','Earn Points','Kids earn points for tasks and good behaviour'],
          ['🎁','Claim Rewards','Spend points on rewards parents define'],
          ['🏆','Leaderboard','Friendly competition keeps everyone motivated'],
        ].map(([icon, title, desc]) => (
          <div key={title} className="feature-card">
            <div className="feature-icon">{icon}</div>
            <h3>{title}</h3>
            <p>{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Header ────────────────────────────────────────────────────────────────────
function Header({ user, onSwitch }) {
  return (
    <header className="app-header">
      <div className="header-inner">
        <div className="logo"><span>{APP_ICON}</span><span>{APP_NAME}</span></div>
        <div className="header-right">
          {user.is_kid && <div className="points-badge">⭐ {user.points}</div>}
          <Avatar name={user.first_name} color={user.avatar_color} size={36} />
          <button className="switch-btn" onClick={onSwitch}>Switch View</button>
        </div>
      </div>
    </header>
  )
}

// ── Bottom Nav ────────────────────────────────────────────────────────────────
function BottomNav({ view, setView, isParent }) {
  const nav = isParent
    ? [['parent','🏠','Home'],['tasks','📋','Tasks'],['behaviors','⭐','Behavior'],['rewards','🎁','Rewards'],['profile','👤','Profile']]
    : [['kid','🏠','Home'],['tasks','📋','Tasks'],['rewards','🎁','Rewards'],['leaderboard','🏆','Board'],['profile','👤','Me']]
  return (
    <nav className="bottom-nav">
      {nav.map(([key, icon, label]) => (
        <button key={key} className={`nav-item${view === key ? ' active' : ''}`} onClick={() => setView(key)}>
          <span className="nav-icon">{icon}</span>
          <span className="nav-label">{label}</span>
        </button>
      ))}
    </nav>
  )
}

// ── Parent Dashboard ──────────────────────────────────────────────────────────
function ParentDashboard({ setView }) {
  const sorted = [...kids].sort((a, b) => b.points - a.points)
  const pending = redemptions.filter(r => r.status === 'pending')
  return (
    <div className="screen">
      <div className="page-header">
        <div><h1 className="page-title">Hey, Mark! 👋</h1><p className="page-sub">Here's how your family is doing.</p></div>
        <Btn sm onClick={() => setView('tasks')}>+ Task</Btn>
      </div>
      <div className="stats-row">
        <div className="stat-card"><div className="stat-val">{kids.length}</div><div className="stat-label">Kids</div></div>
        <div className="stat-card stat-green"><div className="stat-val">{tasks.filter(t => t.completed).length}</div><div className="stat-label">Done Today</div></div>
        <div className="stat-card stat-orange"><div className="stat-val">{pending.length}</div><div className="stat-label">Requests</div></div>
      </div>
      <section className="section">
        <div className="section-hdr"><h2>Your Kids</h2><Btn sm variant="outline">+ Add Kid</Btn></div>
        {sorted.map((kid, i) => (
          <div key={kid.id} className="kid-card">
            <Avatar name={kid.first_name} color={kid.avatar_color} size={48} />
            <div className="kid-info">
              <div className="kid-name">{kid.first_name} {i === 0 && '🥇'}</div>
              <div className="kid-chips">
                <span className="chip chip-gold">⭐ {kid.points} pts</span>
                <span className="chip chip-blue">📋 {kid.pending} tasks</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${Math.min(kid.points, 100)}%`, background: kid.avatar_color }} />
              </div>
            </div>
          </div>
        ))}
      </section>
      {pending.length > 0 && (
        <section className="section">
          <div className="section-hdr"><h2>🎁 Reward Requests</h2><Btn sm variant="outline" onClick={() => setView('redemptions')}>See All</Btn></div>
          {pending.map(r => (
            <div key={r.id} className="redemption-card">
              <div className="redemption-info">
                <span style={{ fontSize: '1.5rem' }}>{r.icon}</span>
                <div><div className="redemption-name"><strong>{r.kid}</strong> wants <strong>{r.reward}</strong></div><div className="muted-sm">{r.points_cost} pts</div></div>
              </div>
              <div className="redemption-actions"><Btn sm variant="green">✓</Btn><Btn sm variant="danger">✗</Btn></div>
            </div>
          ))}
        </section>
      )}
      <section className="section">
        <div className="section-hdr"><h2>Recent Tasks</h2><Btn sm variant="outline" onClick={() => setView('tasks')}>See All</Btn></div>
        {tasks.slice(0, 4).map(t => (
          <div key={t.id} className="task-row">
            <div className="task-dot" style={{ background: priorityColor(t.priority) }} />
            <div className="task-row-info"><div className="task-row-title">{t.title}</div><div className="muted-sm">{t.assigned_to} · {t.points_value} pts</div></div>
            <Badge variant={t.completed ? 'green' : 'grey'}>{t.completed ? 'Done' : 'Pending'}</Badge>
          </div>
        ))}
      </section>
    </div>
  )
}

// ── Kid Dashboard ─────────────────────────────────────────────────────────────
function KidDashboard({ setView }) {
  const kid = { first_name: 'Eva', points: 74, avatar_color: '#F7557A' }
  const myTasks = tasks.filter(t => t.assigned_to === 'Eva' && !t.completed)
  const affordable = rewards.filter(r => r.points_cost <= kid.points)
  return (
    <div className="screen">
      <div className="kid-hero">
        <Avatar name={kid.first_name} color={kid.avatar_color} size={72} />
        <h2 style={{ marginTop: '.75rem', fontWeight: 800 }}>{kid.first_name}</h2>
        <div className="points-hero">
          <span style={{ fontSize: '1.4rem' }}>⭐</span>
          <span className="points-num">{kid.points}</span>
          <span style={{ fontSize: '.85rem', alignSelf: 'flex-end', marginBottom: 2 }}>points</span>
        </div>
        {affordable.length > 0 && <p className="can-afford">🎉 You can afford {affordable.length} reward{affordable.length > 1 ? 's' : ''}!</p>}
      </div>
      <section className="section">
        <div className="section-hdr"><h2>My Tasks</h2><Badge variant="purple">{myTasks.length} left</Badge></div>
        {myTasks.length ? myTasks.map(t => (
          <div key={t.id} className="kid-task-card" style={{ borderLeftColor: priorityColor(t.priority) }}>
            <div className="kid-task-top">
              <span style={{ fontSize: '1.5rem' }}>{catEmoji(t.category)}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700 }}>{t.title}</div>
                <div className="muted-sm">Due: {new Date(t.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</div>
              </div>
              <div className="task-pts">+{t.points_value}<span>pts</span></div>
            </div>
            <Btn full sm>Mark Done ✓</Btn>
          </div>
        )) : <div className="empty-sm">🎉 All done! No tasks right now.</div>}
      </section>
      <section className="section">
        <div className="section-hdr"><h2>🏆 Leaderboard</h2><Btn sm variant="outline" onClick={() => setView('leaderboard')}>Full Board</Btn></div>
        {[...kids].sort((a, b) => b.points - a.points).map((k, i) => (
          <div key={k.id} className={`lb-row${k.first_name === 'Eva' ? ' lb-me' : ''}`}>
            <span className="lb-rank">{i + 1}</span>
            <Avatar name={k.first_name} color={k.avatar_color} size={34} />
            <span style={{ flex: 1, fontWeight: 600 }}>{k.first_name}{k.first_name === 'Eva' ? ' (you)' : ''}</span>
            <span style={{ fontWeight: 700, color: 'var(--primary)' }}>⭐ {k.points}</span>
          </div>
        ))}
      </section>
      <section className="section">
        <div className="section-hdr"><h2>🎁 Rewards</h2><Btn sm variant="outline" onClick={() => setView('rewards')}>See All</Btn></div>
        <div className="rewards-row">
          {rewards.slice(0, 4).map(r => (
            <div key={r.id} className={`reward-preview${r.points_cost > kid.points ? ' reward-locked' : ''}`}>
              <div style={{ fontSize: '1.8rem' }}>{r.icon}</div>
              <div style={{ fontSize: '.75rem', fontWeight: 600 }}>{r.title}</div>
              <div style={{ fontSize: '.7rem', color: 'var(--primary)', fontWeight: 700 }}>{r.points_cost} pts</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

// ── Tasks ─────────────────────────────────────────────────────────────────────
function TasksScreen() {
  const [filter, setFilter] = useState('all')
  const filtered = tasks.filter(t => filter === 'all' ? true : filter === 'done' ? t.completed : !t.completed)
  return (
    <div className="screen">
      <div className="page-header"><h1 className="page-title">Tasks</h1><Btn sm>+ New</Btn></div>
      <div className="filter-tabs">
        {['all', 'pending', 'done'].map(f => (
          <button key={f} className={`filter-tab${filter === f ? ' active' : ''}`} onClick={() => setFilter(f)}>
            {f[0].toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      {filtered.map(t => (
        <div key={t.id} className={`task-card${t.completed ? ' task-done' : ''}`} style={{ borderLeftColor: priorityColor(t.priority) }}>
          <div className="task-card-hdr">
            <span className="cat-badge">{catEmoji(t.category)} {t.category}</span>
            <Badge variant={t.priority === 4 ? 'danger' : t.priority === 3 ? 'orange' : 'purple'}>{{ 4: 'Urgent', 3: 'High', 2: 'Medium', 1: 'Low' }[t.priority]}</Badge>
          </div>
          <div style={{ fontWeight: 700, margin: '.4rem 0' }}>{t.title}</div>
          <div className="meta-row">
            <span className="meta-chip">👤 {t.assigned_to}</span>
            <span className="meta-chip">📅 {new Date(t.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
            <span className="meta-chip" style={{ color: 'var(--primary)', fontWeight: 700 }}>⭐ {t.points_value} pts</span>
          </div>
          <div className="task-card-footer">
            {t.completed ? <Badge variant="green">✓ Completed {t.fun_rating && `· ${t.fun_rating}`}</Badge> : <Btn sm>Mark Done ✓</Btn>}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
function LeaderboardScreen() {
  const sorted = [...kids].sort((a, b) => b.points - a.points)
  const podium = sorted.length >= 3 ? [sorted[1], sorted[0], sorted[2]] : sorted
  return (
    <div className="screen">
      <h1 className="page-title" style={{ marginBottom: '1.25rem' }}>🏆 Leaderboard</h1>
      <div className="podium">
        {podium.map(k => {
          const rank = sorted.indexOf(k) + 1
          return (
            <div key={k.id} className={`podium-place podium-${rank}${k.first_name === 'Eva' ? ' podium-me' : ''}`}>
              <Avatar name={k.first_name} color={k.avatar_color} size={rank === 1 ? 62 : 50} />
              <div style={{ fontWeight: 700, fontSize: '.85rem', marginTop: '.4rem' }}>{k.first_name}</div>
              <div style={{ fontSize: '.8rem', color: 'var(--muted)' }}>{k.points} pts</div>
              <div style={{ fontSize: '1.3rem' }}>{rank === 1 ? '🥇' : rank === 2 ? '🥈' : '🥉'}</div>
            </div>
          )
        })}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '.5rem', marginTop: '1rem' }}>
        {sorted.map((k, i) => (
          <div key={k.id} className={`lb-row${k.first_name === 'Eva' ? ' lb-me' : ''}`}>
            <span className="lb-rank">{i + 1}</span>
            <Avatar name={k.first_name} color={k.avatar_color} size={36} />
            <span style={{ flex: 1, fontWeight: 600 }}>{k.first_name}</span>
            <span style={{ fontWeight: 700, color: 'var(--primary)' }}>⭐ {k.points}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Rewards ───────────────────────────────────────────────────────────────────
function RewardsScreen({ isParent }) {
  const kidPoints = 74
  return (
    <div className="screen">
      <div className="page-header">
        <h1 className="page-title">🎁 Rewards</h1>
        {isParent ? <Btn sm>+ Add</Btn> : <div className="points-badge">⭐ {kidPoints}</div>}
      </div>
      <div className="rewards-grid">
        {rewards.map(r => {
          const locked = !isParent && r.points_cost > kidPoints
          return (
            <div key={r.id} className={`reward-card${locked ? ' reward-locked' : ''}`}>
              <div style={{ fontSize: '2.5rem' }}>{r.icon}</div>
              <div style={{ fontWeight: 700, fontSize: '.95rem' }}>{r.title}</div>
              <div style={{ fontSize: '.8rem', color: 'var(--muted)' }}>{r.description}</div>
              <div style={{ fontWeight: 800, color: 'var(--primary)' }}>{r.points_cost} pts</div>
              {!isParent && (locked
                ? <div style={{ fontSize: '.75rem', color: 'var(--muted)' }}>Need {r.points_cost - kidPoints} more</div>
                : <Btn sm>Redeem!</Btn>)}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Behaviors ─────────────────────────────────────────────────────────────────
function BehaviorsScreen() {
  return (
    <div className="screen">
      <div className="page-header"><h1 className="page-title">Behavior Log</h1><Btn sm>+ Log</Btn></div>
      {behaviors.map(b => (
        <div key={b.id} className={`behavior-card behavior-${b.type}`}>
          <div style={{ fontSize: '1.5rem' }}>{b.type === 'positive' ? '⭐' : '⚠️'}</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700 }}>{b.kid}</div>
            <div style={{ color: 'var(--muted)', fontSize: '.88rem' }}>{b.description}</div>
            <div style={{ fontSize: '.75rem', color: 'var(--muted)' }}>{b.time}</div>
          </div>
          <div className={`behav-pts ${b.type === 'positive' ? 'pts-pos' : 'pts-neg'}`}>{b.type === 'positive' ? '+' : '−'}{b.points}</div>
        </div>
      ))}
    </div>
  )
}

// ── Redemptions ───────────────────────────────────────────────────────────────
function RedemptionsScreen() {
  const pending = redemptions.filter(r => r.status === 'pending')
  const resolved = redemptions.filter(r => r.status !== 'pending')
  return (
    <div className="screen">
      <h1 className="page-title" style={{ marginBottom: '1.25rem' }}>🎁 Reward Requests</h1>
      {pending.length > 0 && <>
        <h2 style={{ fontSize: '1rem', marginBottom: '.75rem' }}>Pending</h2>
        {pending.map(r => (
          <div key={r.id} className="redemption-card" style={{ borderLeft: '4px solid var(--orange)' }}>
            <div className="redemption-info"><span style={{ fontSize: '2rem' }}>{r.icon}</span>
              <div><div style={{ fontWeight: 600 }}><strong>{r.kid}</strong> wants <strong>{r.reward}</strong></div><div className="muted-sm">{r.points_cost} pts · {r.requested_at}</div></div>
            </div>
            <div className="redemption-actions"><Btn variant="green">✓ Approve</Btn><Btn variant="danger">✗ Deny</Btn></div>
          </div>
        ))}
      </>}
      {resolved.length > 0 && <>
        <h2 style={{ fontSize: '1rem', margin: '1rem 0 .75rem' }}>History</h2>
        {resolved.map(r => (
          <div key={r.id} className="redemption-card" style={{ borderLeft: '4px solid var(--green)', opacity: .8 }}>
            <div className="redemption-info"><span style={{ fontSize: '2rem' }}>{r.icon}</span>
              <div><div style={{ fontWeight: 600 }}>{r.kid} — {r.reward}</div><div className="muted-sm">{r.points_cost} pts</div></div>
            </div>
            <Badge variant="green">Approved</Badge>
          </div>
        ))}
      </>}
    </div>
  )
}

// ── Profile ───────────────────────────────────────────────────────────────────
function ProfileScreen({ isParent }) {
  const user = isParent
    ? { first_name: 'Mark', avatar_color: '#6C63FF', is_parent: true, points: 0 }
    : { first_name: 'Eva', avatar_color: '#F7557A', is_kid: true, points: 74 }
  return (
    <div className="screen">
      <div className="profile-header">
        <Avatar name={user.first_name} color={user.avatar_color} size={64} />
        <div>
          <div style={{ fontWeight: 700, fontSize: '1.2rem' }}>{user.first_name}</div>
          <Badge variant={user.is_parent ? 'purple' : 'green'}>{user.is_parent ? 'Parent' : 'Kid'}</Badge>
          {user.is_kid && <div style={{ color: 'var(--primary)', fontWeight: 700, marginTop: '.3rem' }}>⭐ {user.points} points</div>}
        </div>
      </div>
      {!isParent && (
        <section className="section">
          <h2 style={{ fontSize: '1rem', marginBottom: '.75rem' }}>Points History</h2>
          {transactions.map(tx => (
            <div key={tx.id} className="tx-row">
              <span style={{ fontSize: '1.1rem' }}>{txIcon(tx.type)}</span>
              <div style={{ flex: 1 }}><div style={{ fontSize: '.88rem', fontWeight: 500 }}>{tx.description}</div><div className="muted-sm">{tx.time}</div></div>
              <span style={{ fontWeight: 700, color: tx.amount > 0 ? 'var(--green)' : 'var(--red)' }}>{tx.amount > 0 ? '+' : ''}{tx.amount}</span>
            </div>
          ))}
        </section>
      )}
      <Btn full variant="outline" style={{ color: 'var(--red)', borderColor: 'var(--red)', marginTop: '1rem' }}>Sign Out</Btn>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [view, setView] = useState('landing')
  const [isParent, setIsParent] = useState(true)

  const user = isParent
    ? { first_name: 'Mark', avatar_color: '#6C63FF', is_parent: true }
    : { first_name: 'Eva', avatar_color: '#F7557A', is_kid: true, points: 74 }

  if (view === 'landing') return <Landing onEnter={v => { setIsParent(v === 'parent'); setView(v) }} />

  const screens = {
    parent: <ParentDashboard setView={setView} />,
    kid: <KidDashboard setView={setView} />,
    tasks: <TasksScreen />,
    leaderboard: <LeaderboardScreen />,
    rewards: <RewardsScreen isParent={isParent} />,
    behaviors: <BehaviorsScreen />,
    redemptions: <RedemptionsScreen />,
    profile: <ProfileScreen isParent={isParent} />,
  }

  return (
    <div className="app-shell">
      <Header user={user} onSwitch={() => { setIsParent(p => !p); setView(isParent ? 'kid' : 'parent') }} />
      <main className="main">{screens[view] || screens[isParent ? 'parent' : 'kid']}</main>
      <BottomNav view={view} setView={setView} isParent={isParent} />
    </div>
  )
}
