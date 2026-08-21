import { useEffect, useRef, useState } from 'react'
import api from './api'
import { useLocalizedContent } from './i18n.js'
import LanguageToggle from './LanguageToggle.jsx'

const statusStyles = { pending: 'pending', in_progress: 'in_progress', ready: 'ready', delivered: 'delivered', cancelled: 'cancelled' }

function CustomerPortal({ token, language, onLanguageChange }) {
  const contentRef = useRef(null)
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')

  useLocalizedContent(contentRef, language)

  useEffect(() => {
    const loadStatus = () => api.get(`/portal/jobs/${token}/`)
      .then((response) => { setJob(response.data); setError('') })
      .catch(() => setError('رابط متابعة الإصلاح غير صالح أو لم يعد متاحاً.'))
    loadStatus()
    const timer = window.setInterval(loadStatus, 30000)
    return () => window.clearInterval(timer)
  }, [token])

  if (error) return <main className="portal-shell" dir={language === 'ar' ? 'rtl' : 'ltr'} ref={contentRef}><section className="portal-card"><div className="portal-topbar"><span className="eyebrow">AZM · متابعة الإصلاح</span><LanguageToggle language={language} onChange={onLanguageChange} compact /></div><h1>تعذر فتح المتابعة</h1><p>{error}</p></section></main>
  if (!job) return <main className="portal-shell" dir={language === 'ar' ? 'rtl' : 'ltr'} ref={contentRef}><section className="portal-card"><div className="portal-topbar"><span className="eyebrow">AZM · متابعة الإصلاح</span><LanguageToggle language={language} onChange={onLanguageChange} compact /></div><p>جارٍ تحميل حالة المركبة...</p></section></main>

  return <main className="portal-shell" dir={language === 'ar' ? 'rtl' : 'ltr'} ref={contentRef}><section className="portal-card"><header><div><div className="portal-topbar"><span className="eyebrow">AZM · متابعة الإصلاح</span><LanguageToggle language={language} onChange={onLanguageChange} compact /></div><h1>بطاقة {job.job_number}</h1></div><span className={`portal-status ${statusStyles[job.status]}`}>{job.status_label}</span></header><div className="portal-vehicle"><span>المركبة</span><strong>{job.vehicle}</strong></div><div className="portal-grid"><article><span>تاريخ الاستلام</span><strong>{new Date(job.received_at).toLocaleDateString(language === 'ar' ? 'ar-SA' : 'en-GB')}</strong></article><article><span>موعد الإنجاز المتوقع</span><strong>{job.promised_at ? new Date(job.promised_at).toLocaleString(language === 'ar' ? 'ar-SA' : 'en-GB') : 'سيتم التحديث قريباً'}</strong></article></div>{job.invoice && <section className="portal-invoice"><h2>الفاتورة</h2><div><span>الحالة</span><strong>{job.invoice.status_label}</strong></div><div><span>الإجمالي</span><strong>{job.invoice.total} ر.س</strong></div><div><span>المدفوع</span><strong>{job.invoice.amount_paid} ر.س</strong></div></section>}<footer>للاستفسار عن الإصلاح، يرجى التواصل مع إدارة الورشة.</footer></section></main>
}

export default CustomerPortal
