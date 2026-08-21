import { useCallback, useEffect, useState } from 'react'
import api from './api'
import azmLogo from '../../azm_logo.png'

const emptyPlan = { name: '', code: '', monthly_price: '', max_users: 5, is_active: true }
const today = new Date().toISOString().slice(0, 10)
const statusLabels = { trial: 'تجريبي', active: 'نشط', past_due: 'متأخر', suspended: 'معلّق', cancelled: 'ملغي' }

function PlatformAdmin({ user, onLogout }) {
  const [dashboard, setDashboard] = useState(null)
  const [plans, setPlans] = useState([])
  const [workshops, setWorkshops] = useState([])
  const [plan, setPlan] = useState(emptyPlan)
  const [drafts, setDrafts] = useState({})
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [dashboardResponse, plansResponse, workshopsResponse] = await Promise.all([
        api.get('/auth/platform/dashboard/'),
        api.get('/auth/platform/plans/'),
        api.get('/auth/platform/workshops/'),
      ])
      setDashboard(dashboardResponse.data)
      setPlans(plansResponse.data)
      setWorkshops(workshopsResponse.data)
      setDrafts(Object.fromEntries(workshopsResponse.data.map((workshop) => [workshop.id, {
        plan: workshop.subscription?.plan || '',
        status: workshop.subscription?.status || 'trial',
        started_at: workshop.subscription?.started_at || today,
        current_period_end: workshop.subscription?.current_period_end || '',
        auto_renew: workshop.subscription?.auto_renew ?? true,
        notes: workshop.subscription?.notes || '',
      }])))
    } catch (requestError) {
      setError(requestError.response?.status === 403 ? 'هذه اللوحة مخصصة لمشرف المنصة فقط.' : 'تعذر تحميل بيانات إدارة المنصة.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const createPlan = async (event) => {
    event.preventDefault()
    setError(''); setNotice('')
    try {
      await api.post('/auth/platform/plans/', plan)
      setPlan(emptyPlan)
      await refresh()
      setNotice('تم إنشاء خطة الاشتراك.')
    } catch (requestError) {
      setError(Object.values(requestError.response?.data || {}).flat().join(' ') || 'تعذر إنشاء الخطة.')
    }
  }

  const togglePlan = async (item) => {
    await api.patch(`/auth/platform/plans/${item.id}/`, { is_active: !item.is_active })
    await refresh()
  }

  const saveSubscription = async (workshopId) => {
    setError(''); setNotice('')
    const payload = { ...drafts[workshopId], current_period_end: drafts[workshopId].current_period_end || null }
    try {
      await api.patch(`/auth/platform/workshops/${workshopId}/subscription/`, payload)
      await refresh()
      setNotice('تم تحديث اشتراك الورشة وإبطال الجلسات القديمة عند الحاجة.')
    } catch (requestError) {
      setError(Object.values(requestError.response?.data || {}).flat().join(' ') || 'تعذر تحديث الاشتراك.')
    }
  }

  const updateDraft = (id, field, value) => setDrafts((current) => ({ ...current, [id]: { ...current[id], [field]: value } }))

  return <main className="platform-shell" dir="rtl">
    <header className="platform-header">
      <div className="platform-brand"><img src={azmLogo} alt="شعار عزم" /><div><span>AZM PLATFORM</span><h1>إدارة المنصة والاشتراكات</h1></div></div>
      <div className="platform-user"><span>{user.username}</span><a href="/admin/" target="_blank" rel="noreferrer">Django Admin</a><button onClick={onLogout}>تسجيل الخروج</button></div>
    </header>

    {error && <p className="feedback error" role="alert">{error}</p>}
    {notice && <p className="feedback success" role="status">{notice}</p>}
    {loading ? <p className="platform-loading">جارٍ تحميل بيانات المنصة...</p> : <>
      <section className="platform-metrics">
        <Metric label="الورش" value={dashboard?.workshops} />
        <Metric label="الاشتراكات النشطة" value={dashboard?.active_subscriptions} tone="good" />
        <Metric label="التجارب" value={dashboard?.trial_subscriptions} />
        <Metric label="متأخرة" value={dashboard?.past_due_subscriptions} tone="warning" />
        <Metric label="معلقة/ملغاة" value={dashboard?.suspended_subscriptions} tone="danger" />
        <Metric label="دخل شهري متكرر" value={`${dashboard?.monthly_recurring_revenue || 0} ر.س`} tone="money" />
      </section>

      <section className="platform-card">
        <div className="section-heading"><div><h2>خطط الاشتراك</h2><p>عرّف السعر الشهري وحد المستخدمين ثم اربط الخطة بالورش.</p></div><span>{plans.length} خطة</span></div>
        <form className="platform-plan-form" onSubmit={createPlan}>
          <label>اسم الخطة<input required value={plan.name} onChange={(e) => setPlan({ ...plan, name: e.target.value })} /></label>
          <label>الرمز<input required dir="ltr" pattern="[a-z0-9-]+" value={plan.code} onChange={(e) => setPlan({ ...plan, code: e.target.value.toLowerCase() })} /></label>
          <label>السعر الشهري<input required type="number" min="0" step="0.01" value={plan.monthly_price} onChange={(e) => setPlan({ ...plan, monthly_price: e.target.value })} /></label>
          <label>حد المستخدمين<input required type="number" min="1" value={plan.max_users} onChange={(e) => setPlan({ ...plan, max_users: e.target.value })} /></label>
          <button className="primary" type="submit">إضافة الخطة</button>
        </form>
        <div className="plan-grid">{plans.map((item) => <article key={item.id} className={!item.is_active ? 'inactive' : ''}><h3>{item.name}</h3><strong>{item.monthly_price} ر.س</strong><span>{item.max_users} مستخدم · {item.subscriptions_count} اشتراك</span><button className="subtle" onClick={() => togglePlan(item)}>{item.is_active ? 'تعطيل الخطة' : 'تفعيل الخطة'}</button></article>)}</div>
      </section>

      <section className="platform-card">
        <div className="section-heading"><div><h2>الورش والعملاء</h2><p>تغيير الحالة إلى معلّق أو ملغي يمنع دخول جميع حسابات الورشة فورًا.</p></div><span>{workshops.length} ورشة</span></div>
        <div className="platform-workshops">{workshops.map((workshop) => <article key={workshop.id}>
          <div className="workshop-identity"><h3>{workshop.name}</h3><span>المالك: {workshop.owner_username || 'غير محدد'} · {workshop.users_count} مستخدم</span><small>{workshop.city || 'مدينة غير محددة'} · {workshop.phone || 'لا يوجد هاتف'}</small></div>
          <div className="subscription-editor">
            <label>الخطة<select value={drafts[workshop.id]?.plan || ''} onChange={(e) => updateDraft(workshop.id, 'plan', e.target.value)}><option value="">اختر خطة</option>{plans.filter((item) => item.is_active || item.id === workshop.subscription?.plan).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            <label>الحالة<select value={drafts[workshop.id]?.status || 'trial'} onChange={(e) => updateDraft(workshop.id, 'status', e.target.value)}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label>بداية الاشتراك<input type="date" value={drafts[workshop.id]?.started_at || today} onChange={(e) => updateDraft(workshop.id, 'started_at', e.target.value)} /></label>
            <label>نهاية الدورة<input type="date" value={drafts[workshop.id]?.current_period_end || ''} onChange={(e) => updateDraft(workshop.id, 'current_period_end', e.target.value)} /></label>
            <label className="renew-check"><input type="checkbox" checked={drafts[workshop.id]?.auto_renew ?? true} onChange={(e) => updateDraft(workshop.id, 'auto_renew', e.target.checked)} /> تجديد تلقائي</label>
            <button className="primary compact" disabled={!drafts[workshop.id]?.plan} onClick={() => saveSubscription(workshop.id)}>حفظ الاشتراك</button>
          </div>
        </article>)}</div>
      </section>
    </>}
  </main>
}

function Metric({ label, value, tone = '' }) {
  return <article className={tone}><span>{label}</span><strong>{value ?? 0}</strong></article>
}

export default PlatformAdmin
