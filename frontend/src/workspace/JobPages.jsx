import Pagination from './Pagination.jsx'
import { usePagination } from './usePagination.js'

const statusLabels = { pending: 'بانتظار الفحص', in_progress: 'قيد الإصلاح', ready: 'جاهزة للاستلام', delivered: 'تم التسليم', cancelled: 'ملغاة' }

export function DashboardPage({ dashboard, jobs, onStatus, isTechnician, canChangeStatus, canDeliver, onDeliver, onReschedule }) {
  return <>
    <section className="dashboard-intro"><div><h2>{isTechnician ? 'مهامك المسندة' : 'ملخص بطاقات العمل'}</h2><p>تتحدث هذه البيانات مباشرة من قاعدة الورشة.</p></div></section>
    <section className="status-grid">{Object.entries(statusLabels).map(([key, label]) => <article className={`status-card ${key}`} key={key}><span>{label}</span><strong>{dashboard?.counts?.[key] ?? 0}</strong></article>)}</section>
    <JobList jobs={jobs.slice(0, 5)} onStatus={onStatus} isManager={canDeliver} canChangeStatus={canChangeStatus} canDeliver={canDeliver} onDeliver={onDeliver} onReschedule={onReschedule} pageSize={5} />
  </>
}

export function JobsPage({ jobs, isManager, customers, vehicles, services, team, job, setJob, selectedValues, onSubmit, onStatus, onPortalLink, canChangeStatus, canDeliver, onDeliver, onReschedule }) {
  return <>
    <section className="dashboard-intro"><div><h2>{isManager ? 'بطاقات العمل' : 'مهامي'}</h2><p>{isManager ? 'افتح بطاقة جديدة، وحدد العميل والمركبة والفنيين.' : 'تابع البطاقات المتاحة حسب صلاحيات حسابك.'}</p></div></section>
    {isManager && <form className="entry-form job-form" onSubmit={onSubmit}><label>العميل<select required value={job.customer} onChange={(e) => setJob({ ...job, customer: e.target.value, vehicle: '' })}><option value="">اختر العميل</option>{customers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>المركبة<select required value={job.vehicle} onChange={(e) => setJob({ ...job, vehicle: e.target.value })}><option value="">اختر المركبة</option>{vehicles.map((item) => <option key={item.id} value={item.id}>{item.license_plate} — {item.make} {item.model}</option>)}</select></label><label>الخدمات<select multiple value={job.service_ids} onChange={(e) => setJob({ ...job, service_ids: selectedValues(e) })}>{services.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>الفنيون<select multiple value={job.technician_ids} onChange={(e) => setJob({ ...job, technician_ids: selectedValues(e) })}>{team.filter((item) => item.role === 'technician').map((item) => <option key={item.id} value={item.id}>{item.first_name || item.username}</option>)}</select></label><label>التكلفة التقديرية<input type="number" min="0" step="0.01" value={job.estimated_cost} onChange={(e) => setJob({ ...job, estimated_cost: e.target.value })} /></label><label>موعد الإنجاز<input type="datetime-local" value={job.promised_at} onChange={(e) => setJob({ ...job, promised_at: e.target.value })} /></label><label className="wide">وصف العطل<textarea required value={job.complaint} onChange={(e) => setJob({ ...job, complaint: e.target.value })} /></label><label className="wide">نتيجة الفحص (اختياري)<textarea value={job.diagnosis} onChange={(e) => setJob({ ...job, diagnosis: e.target.value })} /></label><button className="primary">فتح بطاقة عمل</button></form>}
    <JobList jobs={jobs} onStatus={onStatus} isManager={isManager} onPortalLink={onPortalLink} canChangeStatus={canChangeStatus} canDeliver={canDeliver} onDeliver={onDeliver} onReschedule={onReschedule} />
  </>
}

export function JobList({ jobs, onStatus, isManager, onPortalLink, canChangeStatus, canDeliver, onDeliver, onReschedule, pageSize }) {
  const pagination = usePagination(jobs, pageSize)
  const formatDate = (value) => value ? new Date(value).toLocaleString('ar-SA') : 'غير محدد'

  return <section className="recent-jobs">
    <div className="section-heading"><h2>البطاقات</h2><span>{jobs.length} بطاقة</span></div>
    {jobs.length ? <>
      <div className="job-table"><div className="job-row job-head"><span>البطاقة</span><span>المركبة والعميل</span><span>العطل والموعد</span><span>الحالة</span></div>{pagination.pageItems.map((item) => <div className="job-row" key={item.id}><strong>{item.job_number}</strong><span>{item.vehicle_label}<small>{item.customer_name}</small></span><span>{item.complaint}<small>التسليم المتوقع: {formatDate(item.promised_at)}</small>{item.promised_at && new Date(item.promised_at) < new Date() && !['ready', 'delivered', 'cancelled'].includes(item.status) && <small className="overdue">متأخرة عن الموعد</small>}</span><span><span className={`job-status ${item.status}`}>{item.status_label}</span>{canChangeStatus && item.status === 'pending' && <button className="text-action" type="button" onClick={() => onStatus(item.id, 'in_progress')}>بدء العمل</button>}{canChangeStatus && item.status === 'in_progress' && <button className="text-action" type="button" onClick={() => onStatus(item.id, 'ready')}>جاهزة للتسليم</button>}{canDeliver && item.status === 'ready' && <button className="text-action" type="button" onClick={() => onDeliver(item.id)}>تسليم للعميل</button>}{isManager && !['delivered', 'cancelled'].includes(item.status) && <button className="text-action" type="button" onClick={() => onReschedule(item)}>تحديث الموعد</button>}{isManager && onPortalLink && <button className="text-action" type="button" onClick={() => onPortalLink(item.id)}>رابط العميل</button>}</span></div>)}</div>
      <Pagination {...pagination} onPageChange={pagination.setPage} itemLabel="بطاقة" />
    </> : <p className="empty-state">لا توجد بطاقات عمل حالياً.</p>}
  </section>
}
