import {Clock3,LockKeyhole,LogOut,Monitor,Shield,UserRound} from 'lucide-react'
import type {QueryResult,User} from '../types'
import {Badge,Card,Empty} from '../components/ui'

export function HistoryPage({history}:{history:QueryResult[]}) {
  return <div className="page-stack">
    <div className="page-heading"><div><p className="eyebrow">PRIVATE TO YOU</p><h1>Search History</h1><p>Your last 100 questions and their answer status.</p></div></div>
    <Card>{history.length ? <div className="history-list">{history.map(query => <div key={query.id}>
      <div className="history-icon"><Clock3/></div><div><strong>{query.question}</strong><span>{new Date(query.created_at).toLocaleString()} · {(query.total_latency_ms/1000).toFixed(2)}s</span></div>
      <Badge tone={query.answer?.insufficient_evidence?'unsupported':'supported'}>{query.answer?.insufficient_evidence?'insufficient':'answered'}</Badge>
    </div>)}</div> : <Empty icon={<Clock3/>} title="No search history" body="Questions you ask will be retained here for your account."/>}</Card>
  </div>
}

export function SettingsPage({user,onSignOut}:{user:User;onSignOut:()=>void}) {
  return <div className="page-stack">
    <div className="page-heading"><div><p className="eyebrow">YOUR ACCOUNT</p><h1>Settings</h1><p>Account details, preferences, and session controls.</p></div></div>
    <div className="settings-grid">
      <Card><div className="section-title"><div><p className="eyebrow">PROFILE</p><h2>Account details</h2></div><UserRound/></div><label>Display name<input value={user.display_name} readOnly/></label><label>Email<input value={user.email} readOnly/></label></Card>
      <Card><div className="section-title"><div><p className="eyebrow">PREFERENCES</p><h2>Workspace behavior</h2></div><Monitor/></div><p className="setting-row"><span><strong>Theme</strong><small>Use the header control to switch themes.</small></span><Badge>Device-local</Badge></p><p className="setting-row"><span><strong>Answer mode</strong><small>Evidence-first extractive responses.</small></span><Badge>Extractive</Badge></p></Card>
      <Card><div className="section-title"><div><p className="eyebrow">SECURITY</p><h2>Current session</h2></div><Shield/></div><p className="security-copy"><LockKeyhole/>Passwords are Argon2-hashed. Sessions expire automatically, and every document request is scoped to its owner.</p><button className="button danger-button" onClick={onSignOut}><LogOut size={16}/>Sign out on this device</button></Card>
    </div>
  </div>
}
