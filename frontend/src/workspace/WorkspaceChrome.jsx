import LanguageToggle from '../LanguageToggle.jsx'
import azmLogo from '../../../azm_logo.png'

const roleLabels = { owner: 'مالك الورشة', manager: 'مدير الورشة', accountant: 'محاسب', technician: 'فني', receptionist: 'موظف استقبال', storekeeper: 'أمين مخزن' }

export function WorkspaceNavigation({ user, navItems, view, onSelect, onLogout }) {
  return <aside className="side-nav">
    <div className="brand-mini"><img src={azmLogo} alt="Azm logo" /></div>
    <p>{user.workshop?.name}</p>
    {navItems.map(([id, label]) => <button type="button" key={id} className={view === id ? 'nav-active' : ''} onClick={() => onSelect(id)}>{label}</button>)}
    <button type="button" className="nav-logout" onClick={onLogout}>تسجيل الخروج</button>
  </aside>
}

export function WorkspaceHeader({ user, title, language, onLanguageChange }) {
  return <header className="workspace-header">
    <div><span className="eyebrow">إدارة الورشة</span><h1>{title}</h1></div>
    <div className="header-actions"><LanguageToggle language={language} onChange={onLanguageChange} compact /><div className="user-chip">{user.first_name || user.username}<small>{roleLabels[user.role] || user.role}</small></div></div>
  </header>
}
