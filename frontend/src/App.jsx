import { useEffect, useRef, useState } from 'react'
import api from './api'
import './App.css'
import Workspace from './Workspace.jsx'
import CustomerPortal from './CustomerPortal.jsx'
import PlatformAdmin from './PlatformAdmin.jsx'
import { getInitialLanguage, setDocumentLanguage, useLocalizedContent } from './i18n.js'
import LanguageToggle from './LanguageToggle.jsx'
import azmLogo from '../../azm_logo.png'

const emptyRegisterForm = {
  workshop_name: '',
  first_name: '',
  last_name: '',
  username: '',
  email: '',
  password: '',
}

const portalToken = window.location.pathname.match(/^\/portal\/([0-9a-f-]{36})\/?$/i)?.[1]

function App() {
  const [language, setLanguage] = useState(getInitialLanguage)

  useEffect(() => {
    localStorage.setItem('azm_language', language)
    setDocumentLanguage(language)
  }, [language])

  return portalToken
    ? <CustomerPortal token={portalToken} language={language} onLanguageChange={setLanguage} />
    : <AzmApp language={language} onLanguageChange={setLanguage} />
}

function AzmApp({ language, onLanguageChange }) {
  const contentRef = useRef(null)
  const [mode, setMode] = useState('login')
  const [login, setLogin] = useState({ username: '', password: '' })
  const [register, setRegister] = useState(emptyRegisterForm)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [user, setUser] = useState(null)
  const [serverUrl, setServerUrl] = useState(() => window.azmDesktop?.apiBaseUrl || '')

  useLocalizedContent(contentRef, language)

  const resetFeedback = () => {
    setMessage('')
    setError('')
  }

  const loadSession = async () => {
    const profileResponse = await api.get('/auth/me/')
    setUser(profileResponse.data)
  }

  useEffect(() => {
    if (!localStorage.getItem('azm_access_token')) return
    loadSession().catch(() => {
      localStorage.removeItem('azm_access_token')
      localStorage.removeItem('azm_refresh_token')
    })
  }, [])

  useEffect(() => {
    const expireSession = () => {
      setUser(null)
      setMode('login')
      setError('انتهت الجلسة. سجّل الدخول مرة أخرى للمتابعة.')
    }
    window.addEventListener('azm:session-expired', expireSession)
    return () => window.removeEventListener('azm:session-expired', expireSession)
  }, [])

  const submitLogin = async (event) => {
    event.preventDefault()
    resetFeedback()
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login/', login)
      localStorage.setItem('azm_access_token', data.access)
      localStorage.setItem('azm_refresh_token', data.refresh)
      await loadSession()
    } catch (requestError) {
      if (requestError.response?.status === 401) {
        setError('اسم المستخدم أو كلمة المرور غير صحيحة.')
      } else if (requestError.response?.status === 403) {
        setError(requestError.response?.data?.detail || 'هذا الحساب غير مخول بالدخول أو اشتراك الورشة غير نشط.')
      } else if (!requestError.response) {
        setError('تعذر الاتصال بخادم عزم. تحقق من الإنترنت وعنوان الخادم، ثم اضغط حفظ الاتصال.')
      } else {
        setError('الخادم متصل لكنه لم يتمكن من إتمام تسجيل الدخول. حاول مجدداً أو تواصل مع مدير النظام.')
      }
    } finally {
      setLoading(false)
    }
  }

  const submitRegistration = async (event) => {
    event.preventDefault()
    resetFeedback()
    setLoading(true)
    try {
      await api.post('/auth/register/', register)
      setRegister(emptyRegisterForm)
      setMode('login')
      setMessage('تم إنشاء الورشة وحساب المالك. يمكنك تسجيل الدخول الآن.')
    } catch (requestError) {
      const details = requestError.response?.data
      setError(details ? Object.values(details).flat().join(' ') : 'تعذر إنشاء الحساب. راجع البيانات وحاول مجدداً.')
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('azm_access_token')
    localStorage.removeItem('azm_refresh_token')
    setUser(null)
    setMode('login')
  }

  const saveDesktopServer = async (event) => {
    event.preventDefault()
    resetFeedback()
    try {
      const normalizedUrl = await window.azmDesktop.saveApiBaseUrl(serverUrl)
      const healthUrl = new URL('/healthz/', normalizedUrl).toString()
      const response = await fetch(healthUrl, { signal: AbortSignal.timeout(10000) })
      if (!response.ok) throw new Error(`الخادم أعاد حالة ${response.status}.`)
      window.location.reload()
    } catch (requestError) {
      setError(requestError.name === 'TimeoutError'
        ? 'تم حفظ العنوان، لكن انتهت مهلة الاتصال بالخادم. تحقق من الشبكة ثم أعد تشغيل التطبيق.'
        : requestError.message || 'تعذر حفظ عنوان الخادم. استخدم عنوان HTTPS صالحاً ينتهي بـ /api.')
    }
  }

  if (user) {
    return user.is_superuser
      ? <PlatformAdmin user={user} onLogout={logout} />
      : <Workspace user={user} onLogout={logout} language={language} onLanguageChange={onLanguageChange} />
  }

  return (
    <main className="page-shell" dir={language === 'ar' ? 'rtl' : 'ltr'} ref={contentRef}>
      <section className="brand-panel">
        <img className="auth-logo" src={azmLogo} alt="Azm logo" />
        <span className="eyebrow">AZM · إدارة ورش السيارات</span>
        <h1>عزمٌ يضبط<br />سير العمل.</h1>
        <p>منصة موحدة لورش السيارات، تبدأ ببيانات آمنة وصلاحيات واضحة لكل فريق العمل.</p>
        <div className="phase-chip">المرحلة 1 · إدارة الورشة</div>
      </section>

      <section className="auth-panel" aria-label="المصادقة">
        <div className="language-control"><LanguageToggle language={language} onChange={onLanguageChange} /></div>
        {window.azmDesktop && <form className="desktop-server-form" onSubmit={saveDesktopServer}>
          <label>عنوان خادم عزم<input required type="url" dir="ltr" value={serverUrl} onChange={(event) => setServerUrl(event.target.value)} placeholder="https://api.example.com/api" /></label>
          <p>يُضبط مرة واحدة بواسطة مدير النظام، ثم يستخدم الجميع الحسابات نفسها.</p>
          <button className="subtle" type="submit">حفظ الاتصال</button>
        </form>}
        <div className="tabs" role="tablist" aria-label="خيارات المصادقة">
          <button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); resetFeedback() }} type="button">تسجيل الدخول</button>
          <button className={mode === 'register' ? 'active' : ''} onClick={() => { setMode('register'); resetFeedback() }} type="button">إنشاء ورشة</button>
        </div>

        {message && <p className="feedback success" role="status">{message}</p>}
        {error && <p className="feedback error" role="alert">{error}</p>}

        {mode === 'login' ? (
          <form className="auth-form" onSubmit={submitLogin}>
            <h2>أهلاً بعودتك</h2>
            <label>اسم المستخدم<input required value={login.username} onChange={(e) => setLogin({ ...login, username: e.target.value })} autoComplete="username" /></label>
            <label>كلمة المرور<input required type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} autoComplete="current-password" /></label>
            <button className="primary" disabled={loading} type="submit">{loading ? 'جارٍ التحقق...' : 'دخول'}</button>
          </form>
        ) : (
          <form className="auth-form" onSubmit={submitRegistration}>
            <h2>أسّس ورشتك</h2>
            <label>اسم الورشة<input required value={register.workshop_name} onChange={(e) => setRegister({ ...register, workshop_name: e.target.value })} /></label>
            <div className="two-columns"><label>الاسم الأول<input required value={register.first_name} onChange={(e) => setRegister({ ...register, first_name: e.target.value })} /></label><label>اسم العائلة<input required value={register.last_name} onChange={(e) => setRegister({ ...register, last_name: e.target.value })} /></label></div>
            <label>اسم المستخدم<input required value={register.username} onChange={(e) => setRegister({ ...register, username: e.target.value })} autoComplete="username" /></label>
            <label>البريد الإلكتروني<input required type="email" value={register.email} onChange={(e) => setRegister({ ...register, email: e.target.value })} autoComplete="email" /></label>
            <label>كلمة المرور<input required type="password" minLength="8" value={register.password} onChange={(e) => setRegister({ ...register, password: e.target.value })} autoComplete="new-password" /></label>
            <button className="primary" disabled={loading} type="submit">{loading ? 'جارٍ الإنشاء...' : 'إنشاء الحساب'}</button>
          </form>
        )}
      </section>
    </main>
  )
}

export default App
