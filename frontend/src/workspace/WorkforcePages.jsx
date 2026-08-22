import Pagination from './Pagination.jsx'
import { usePagination } from './usePagination.js'

export function TasksPage({ tasks, isManager, jobs, employees, task, setTask, onSubmit, onTaskAction, pageSize }) {
  const pagination = usePagination(tasks, pageSize)

  return <>
    <section className="dashboard-intro"><div><h2>{isManager ? 'مهام الفريق' : 'مهامي التفصيلية'}</h2><p>{isManager ? 'أنشئ مهمة مستقلة لكل فني في بطاقة العمل.' : 'ابدأ المهمة ثم أكملها لتسجيل الوقت واحتساب العمولة.'}</p></div></section>
    {isManager && <section className="form-card"><form className="entry-form" onSubmit={onSubmit}><label>بطاقة العمل<select required value={task.job_card} onChange={(e) => setTask({ ...task, job_card: e.target.value })}><option value="">اختر البطاقة</option>{jobs.map((item) => <option key={item.id} value={item.id}>{item.job_number} — {item.vehicle_label}</option>)}</select></label><label>الفني<select required value={task.employee} onChange={(e) => setTask({ ...task, employee: e.target.value })}><option value="">اختر الفني</option>{employees.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.user_name} — {item.job_title}</option>)}</select></label><label>اسم المهمة<input required value={task.title} onChange={(e) => setTask({ ...task, title: e.target.value })} /></label><label>الساعات التقديرية<input required type="number" min="0" step="0.25" value={task.estimated_hours} onChange={(e) => setTask({ ...task, estimated_hours: e.target.value })} /></label><label className="wide">الوصف<textarea value={task.description} onChange={(e) => setTask({ ...task, description: e.target.value })} /></label><button className="primary">إسناد المهمة</button></form></section>}
    <section className="recent-jobs">
      <div className="section-heading"><h2>المهام</h2><span>{tasks.length} مهمة</span></div>
      {tasks.length ? <>
        <div className="record-list">{pagination.pageItems.map((item) => <div className="task-row" key={item.id}><div><strong>{item.title}</strong><small>{item.job_number} · {item.employee_name || 'فني'}</small></div><span className={`job-status ${item.status}`}>{item.status_label}</span><span>{item.actual_minutes} دقيقة</span><span>{item.status === 'not_started' && <button className="text-action" type="button" onClick={() => onTaskAction(item.id, 'start')}>بدء</button>}{item.status === 'in_progress' && <button className="text-action" type="button" onClick={() => onTaskAction(item.id, 'complete')}>إكمال</button>}</span></div>)}</div>
        <Pagination {...pagination} onPageChange={pagination.setPage} itemLabel="مهمة" />
      </> : <p className="empty-state">لا توجد مهام مسندة.</p>}
    </section>
  </>
}

export function EmployeesPage({ employees, team, employee, setEmployee, onSubmit, onDelete, pageSize }) {
  const employeeUserIds = new Set(employees.map((item) => item.user))
  const availableTechnicians = team.filter((item) => item.role === 'technician' && !employeeUserIds.has(item.id))
  const pagination = usePagination(employees, pageSize)

  return <>
    <section className="dashboard-intro"><div><h2>ملفات الموظفين</h2><p>أضف بيانات الفني ونسبة عمولته بعد إنشاء حسابه من شاشة فريق العمل.</p></div></section>
    <section className="form-card"><form className="entry-form" onSubmit={onSubmit}><label>حساب الفني<select required value={employee.user} onChange={(e) => setEmployee({ ...employee, user: e.target.value })}><option value="">اختر حساب الفني</option>{availableTechnicians.map((item) => <option key={item.id} value={item.id}>{item.first_name || item.username} {item.last_name}</option>)}</select></label><label>المسمى الوظيفي<input required value={employee.job_title} onChange={(e) => setEmployee({ ...employee, job_title: e.target.value })} /></label><label>تاريخ التوظيف<input required type="date" value={employee.hired_at} onChange={(e) => setEmployee({ ...employee, hired_at: e.target.value })} /></label><label>نسبة العمولة %<input required type="number" min="0" max="100" step="0.01" value={employee.commission_rate} onChange={(e) => setEmployee({ ...employee, commission_rate: e.target.value })} /></label><label className="wide">ملاحظات<textarea value={employee.notes} onChange={(e) => setEmployee({ ...employee, notes: e.target.value })} /></label><button className="primary">إنشاء ملف الموظف</button></form></section>
    <section className="recent-jobs">
      <div className="section-heading"><h2>الموظفون</h2><span>{employees.length} موظف</span></div>
      {employees.length ? <>
        <div className="record-list">{pagination.pageItems.map((item) => <div className="record-row" key={item.id}><strong>{item.user_name}</strong><span>{item.job_title}</span><span>عمولة {item.commission_rate}%</span><button className="delete-action" type="button" onClick={() => onDelete(item.id)}>حذف</button></div>)}</div>
        <Pagination {...pagination} onPageChange={pagination.setPage} itemLabel="موظف" />
      </> : <p className="empty-state">أنشئ ملفاً لفني حتى يمكن إسناد المهام إليه.</p>}
    </section>
  </>
}

export function CommissionsPage({ commissions, onGenerate, pageSize }) {
  const total = commissions.reduce((sum, item) => sum + Number(item.amount), 0)
  const pagination = usePagination(commissions, pageSize)

  return <>
    <section className="dashboard-intro"><div><h2>تقرير العمولات</h2><p>يُحتسب من قيمة الخدمات والقطع للبطاقات المسلّمة، ويُوزّع بالتساوي على الفنيين الذين أكملوا مهاماً فيها.</p></div><button className="primary compact" type="button" onClick={onGenerate}>احتساب الشهر الحالي</button></section>
    <section className="inventory-summary"><article><span>إجمالي العمولات</span><strong>{total.toFixed(2)} ر.س</strong></article><article><span>سجلات الاستحقاق</span><strong>{commissions.length}</strong></article><article><span>الحالة</span><strong>جاهز</strong></article></section>
    <section className="recent-jobs">
      <div className="section-heading"><h2>التفاصيل</h2></div>
      {commissions.length ? <>
        <div className="record-list">{pagination.pageItems.map((item) => <div className="record-row" key={item.id}><strong>{item.employee_name || 'فني'}</strong><span>{item.job_number}</span><span>{item.commission_rate}% من {item.basis_amount} ر.س</span><strong>{item.amount} ر.س</strong></div>)}</div>
        <Pagination {...pagination} onPageChange={pagination.setPage} itemLabel="عمولة" />
      </> : <p className="empty-state">لا توجد عمولات لهذا الشهر. سلّم بطاقة وأكمل مهامها ثم شغّل الاحتساب.</p>}
    </section>
  </>
}
