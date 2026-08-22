import { useState } from 'react'
import Pagination from './Pagination.jsx'
import { usePagination } from './usePagination.js'

export default function DocumentsPage({ documents, alerts, customers, vehicles, employees, onUpload, onDownload, onAcknowledge, remove, pageSize }) {
  const [form, setForm] = useState({ name: '', document_type: '', expires_at: '', ownerType: '', ownerId: '' })
  const [file, setFile] = useState(null)
  const alertPagination = usePagination(alerts, pageSize)
  const documentPagination = usePagination(documents, pageSize)
  const ownerOptions = form.ownerType === 'customer' ? customers : form.ownerType === 'vehicle' ? vehicles : employees
  const optionLabel = (item) => {
    if (form.ownerType === 'customer') return item.name
    if (form.ownerType === 'vehicle') return `${item.license_plate} — ${item.make} ${item.model}`
    return `${item.user_name} — ${item.job_title}`
  }
  const upload = (event) => {
    event.preventDefault()
    if (!file) return
    const data = new FormData()
    data.append('name', form.name)
    data.append('document_type', form.document_type)
    if (form.expires_at) data.append('expires_at', form.expires_at)
    if (form.ownerType && form.ownerId) data.append(form.ownerType, form.ownerId)
    data.append('file', file)
    onUpload(data)
    setForm({ name: '', document_type: '', expires_at: '', ownerType: '', ownerId: '' })
    setFile(null)
  }

  return <>
    <section className="dashboard-intro"><div><h2>أرشفة الوثائق</h2><p>تُخزن الملفات مشفرة، ولا تُفك إلا أثناء تنزيلها للمستخدم المصرح له.</p></div></section>
    <section className="form-card"><form className="entry-form" onSubmit={upload}><label>اسم الوثيقة<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label>نوع الوثيقة<input required placeholder="رخصة، عقد، شهادة..." value={form.document_type} onChange={(e) => setForm({ ...form, document_type: e.target.value })} /></label><label>تاريخ الانتهاء<input type="date" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} /></label><label>ربط بـ<select value={form.ownerType} onChange={(e) => setForm({ ...form, ownerType: e.target.value, ownerId: '' })}><option value="">الورشة فقط</option><option value="customer">عميل</option><option value="vehicle">مركبة</option><option value="employee">موظف</option></select></label>{form.ownerType && <label>الجهة<select required value={form.ownerId} onChange={(e) => setForm({ ...form, ownerId: e.target.value })}><option value="">اختر</option>{ownerOptions.map((item) => <option key={item.id} value={item.id}>{optionLabel(item)}</option>)}</select></label>}<label>الملف<input required type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label><button className="primary">رفع وتشفير الوثيقة</button></form></section>
    <section className="recent-jobs">
      <div className="section-heading"><h2>تنبيهات انتهاء الصلاحية</h2><span>{alerts.filter((item) => !item.acknowledged_at).length} جديد</span></div>
      {alerts.length ? <div className="record-list">{alertPagination.pageItems.map((item) => <div className={`record-row ${item.acknowledged_at ? '' : 'low-stock-row'}`} key={item.id}><strong>{item.document_name}</strong><span>ينتهي: {item.expires_at}</span><span>خلال {item.days_before} يوم</span>{item.acknowledged_at ? <span>تمت القراءة</span> : <button className="text-action" type="button" onClick={() => onAcknowledge(item.id)}>تأكيد</button>}</div>)}</div> : <p className="empty-state">لا توجد تنبيهات صلاحية حالياً.</p>}
      <Pagination {...alertPagination} onPageChange={alertPagination.setPage} itemLabel="تنبيه وثيقة" />
    </section>
    <section className="recent-jobs">
      <div className="section-heading"><h2>الوثائق المؤرشفة</h2><span>{documents.length} وثيقة</span></div>
      {documents.length ? <div className="record-list">{documentPagination.pageItems.map((item) => <div className="document-row" key={item.id}><div><strong>{item.name}</strong><small>{item.document_type} · {item.owner_label}</small></div><span>{item.expires_at || 'بلا انتهاء'}</span><span>{item.original_filename}</span><div><button className="text-action" type="button" onClick={() => onDownload(item)}>تنزيل</button><button className="delete-action" type="button" onClick={() => remove('/documents/documents/', item.id)}>حذف</button></div></div>)}</div> : <p className="empty-state">لا توجد وثائق مؤرشفة بعد.</p>}
      <Pagination {...documentPagination} onPageChange={documentPagination.setPage} itemLabel="وثيقة" />
    </section>
  </>
}
