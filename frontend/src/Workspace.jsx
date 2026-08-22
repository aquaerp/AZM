import { useCallback, useEffect, useRef, useState } from 'react'
import api from './api'
import { useLocalizedContent } from './i18n.js'
import { emptyExpense, emptyVoucher } from './workspace/AccountingDefaults.js'
import AccountingPage from './workspace/AccountingPage.jsx'
import { DashboardPage, JobsPage } from './workspace/JobPages.jsx'
import InventoryPage from './workspace/InventoryPage.jsx'
import DocumentsPage from './workspace/DocumentsPage.jsx'
import PointOfSalePage from './workspace/PointOfSalePage.jsx'
import RecordsPage from './workspace/RecordsPage.jsx'
import { emptyWorkshopProfile } from './workspace/WorkshopSettingsDefaults.js'
import WorkshopSettingsPage from './workspace/WorkshopSettingsPage.jsx'
import { WorkspaceHeader, WorkspaceNavigation } from './workspace/WorkspaceChrome.jsx'
import { CommissionsPage, EmployeesPage, TasksPage } from './workspace/WorkforcePages.jsx'

const emptyCustomer = { name: '', phone: '', email: '', notes: '' }
const emptyVehicle = { customer: '', license_plate: '', make: '', model: '', model_year: '', vin: '', color: '', mileage: '', notes: '' }
const emptyService = { name: '', description: '', base_price: '0.00', is_active: true }
const emptyTeamMember = { username: '', password: '', first_name: '', last_name: '', email: '', role: 'technician' }
const emptyJob = { customer: '', vehicle: '', complaint: '', diagnosis: '', estimated_cost: '0.00', promised_at: '', service_ids: [], technician_ids: [] }
const emptySupplier = { name: '', contact_name: '', phone: '', email: '', notes: '', is_active: true }
const emptyPart = { name: '', sku: '', description: '', supplier: '', quantity: '0', reorder_level: '0', purchase_price: '0.00', sale_price: '0.00', is_active: true }
const emptyPartUsage = { job_card: '', part: '', quantity: '1' }
const emptyPartRequest = { job_card: '', part: '', quantity: '1', notes: '' }
const today = new Date().toISOString().slice(0, 10)
const emptyEmployee = { user: '', job_title: 'فني', hired_at: today, commission_rate: '0.00', notes: '' }
const emptyTask = { job_card: '', employee: '', title: '', description: '', estimated_hours: '0.00' }
const getError = (error, fallback) => {
  const data = error.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (typeof data.detail === 'string') return data.detail
  return Object.values(data).flatMap((value) => typeof value === 'object' ? Object.values(value) : value).join(' ')
}

function Workspace({ user, onLogout, language, onLanguageChange }) {
  const contentRef = useRef(null)
  const isManager = user.role === 'owner' || user.role === 'manager'
  const isOwner = user.role === 'owner'
  const isOperational = isManager || user.role === 'receptionist'
  const isFinancial = isManager || user.role === 'accountant'
  const canUseInventory = isManager || ['accountant', 'receptionist', 'storekeeper', 'technician'].includes(user.role)
  const canManageInventory = isManager || user.role === 'storekeeper'
  const canIssueParts = isManager || ['accountant', 'receptionist', 'storekeeper'].includes(user.role)
  const [view, setView] = useState('dashboard')
  const [dashboard, setDashboard] = useState(null)
  const [customers, setCustomers] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [services, setServices] = useState([])
  const [team, setTeam] = useState([])
  const [jobs, setJobs] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [parts, setParts] = useState([])
  const [lowStock, setLowStock] = useState([])
  const [alerts, setAlerts] = useState([])
  const [partUsages, setPartUsages] = useState([])
  const [partRequests, setPartRequests] = useState([])
  const [employees, setEmployees] = useState([])
  const [tasks, setTasks] = useState([])
  const [commissions, setCommissions] = useState([])
  const [invoices, setInvoices] = useState([])
  const [expenses, setExpenses] = useState([])
  const [vouchers, setVouchers] = useState([])
  const [profitLoss, setProfitLoss] = useState(null)
  const [documents, setDocuments] = useState([])
  const [documentAlerts, setDocumentAlerts] = useState([])
  const [customer, setCustomer] = useState(emptyCustomer)
  const [vehicle, setVehicle] = useState(emptyVehicle)
  const [service, setService] = useState(emptyService)
  const [teamMember, setTeamMember] = useState(emptyTeamMember)
  const [job, setJob] = useState(emptyJob)
  const [supplier, setSupplier] = useState(emptySupplier)
  const [part, setPart] = useState(emptyPart)
  const [partUsage, setPartUsage] = useState(emptyPartUsage)
  const [partRequest, setPartRequest] = useState(emptyPartRequest)
  const [employee, setEmployee] = useState(emptyEmployee)
  const [task, setTask] = useState(emptyTask)
  const [expense, setExpense] = useState(emptyExpense)
  const [voucher, setVoucher] = useState(emptyVoucher)
  const [workshopProfile, setWorkshopProfile] = useState(emptyWorkshopProfile)
  const [workshopLogo, setWorkshopLogo] = useState(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useLocalizedContent(contentRef, language)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const requests = {
        dashboard: api.get('/workshop/job-cards/dashboard/'), jobs: api.get('/workshop/job-cards/'), tasks: api.get('/workforce/tasks/'),
      }
      if (isOperational || isFinancial) Object.assign(requests, { customers: api.get('/workshop/customers/'), vehicles: api.get('/workshop/vehicles/'), services: api.get('/workshop/services/') })
      if (isManager) Object.assign(requests, { team: api.get('/auth/team/'), employees: api.get('/workforce/employees/'), documents: api.get('/documents/documents/'), documentAlerts: api.get('/documents/alerts/') })
      if (canUseInventory) Object.assign(requests, { suppliers: api.get('/inventory/suppliers/'), parts: api.get('/inventory/parts/'), lowStock: api.get('/inventory/parts/low-stock/'), partUsages: api.get('/inventory/part-usages/'), partRequests: api.get('/inventory/part-requests/') })
      if (canManageInventory) requests.alerts = api.get('/inventory/alerts/')
      if (isFinancial) Object.assign(requests, { commissions: api.get('/workforce/commissions/'), invoices: api.get('/accounting/invoices/'), expenses: api.get('/accounting/expenses/'), profitLoss: api.get('/accounting/reports/profit-loss/'), vouchers: api.get('/accounting/vouchers/') })
      const entries = Object.entries(requests)
      const values = await Promise.all(entries.map(([, request]) => request))
      const responses = Object.fromEntries(entries.map(([key], index) => [key, values[index].data]))
      setDashboard(responses.dashboard); setJobs(responses.jobs); setTasks(responses.tasks)
      if (responses.customers) setCustomers(responses.customers)
      if (responses.vehicles) setVehicles(responses.vehicles)
      if (responses.services) setServices(responses.services)
      if (responses.team) setTeam(responses.team)
      if (responses.suppliers) setSuppliers(responses.suppliers)
      if (responses.parts) setParts(responses.parts)
      if (responses.lowStock) setLowStock(responses.lowStock)
      if (responses.alerts) setAlerts(responses.alerts)
      if (responses.partUsages) setPartUsages(responses.partUsages)
      if (responses.partRequests) setPartRequests(responses.partRequests)
      if (responses.employees) setEmployees(responses.employees)
      if (responses.commissions) setCommissions(responses.commissions)
      if (responses.invoices) setInvoices(responses.invoices)
      if (responses.expenses) setExpenses(responses.expenses)
      if (responses.profitLoss) setProfitLoss(responses.profitLoss)
      if (responses.documents) setDocuments(responses.documents)
      if (responses.documentAlerts) setDocumentAlerts(responses.documentAlerts)
      if (responses.vouchers) setVouchers(responses.vouchers)
      if (isOwner) {
        const { data } = await api.get('/auth/workshop/')
        setWorkshopProfile({ ...emptyWorkshopProfile, ...data })
      }
    } catch (requestError) {
      setError(getError(requestError, 'تعذر تحميل بيانات الورشة. تأكد من تشغيل الخادم.'))
    } finally {
      setLoading(false)
    }
  }, [isManager, isOwner, isOperational, isFinancial, canUseInventory, canManageInventory])

  useEffect(() => { refresh() }, [refresh])

  const submit = async (event, endpoint, value, reset, message) => {
    event.preventDefault()
    setError('')
    setNotice('')
    try {
      await api.post(endpoint, value)
      reset()
      await refresh()
      setNotice(message)
    } catch (requestError) {
      setError(getError(requestError, 'تعذر حفظ البيانات.'))
    }
  }

  const update = async (endpoint, value, message) => {
    setError('')
    setNotice('')
    try {
      await api.patch(endpoint, value)
      await refresh()
      setNotice(message)
      return true
    } catch (requestError) {
      setError(getError(requestError, 'تعذر تحديث البيانات.'))
      return false
    }
  }

  const remove = async (endpoint, id) => {
    if (!window.confirm('هل تريد حذف هذا السجل؟')) return
    setError('')
    try {
      await api.delete(`${endpoint}${id}/`)
      await refresh()
      setNotice('تم حذف السجل.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر حذف السجل المرتبط ببطاقة عمل.'))
    }
  }

  const updateJobStatus = async (id, status) => {
    setError('')
    try {
      await api.patch(`/workshop/job-cards/${id}/status/`, { status })
      await refresh()
      setNotice('تم تحديث حالة بطاقة العمل.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر تحديث الحالة.'))
    }
  }

  const deliverJob = async (id) => {
    if (!window.confirm('تأكيد تسليم المركبة للعميل وإغلاق بطاقة العمل؟')) return
    setError('')
    try {
      await api.post(`/workshop/job-cards/${id}/deliver/`)
      await refresh()
      setNotice('تم تسليم المركبة وتوثيق وقت ومنفذ التسليم.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر تسليم بطاقة العمل.'))
    }
  }

  const rescheduleJob = async (jobCard) => {
    const current = jobCard.promised_at ? new Date(jobCard.promised_at).toISOString().slice(0, 16) : ''
    const promisedAt = window.prompt('أدخل موعد التسليم المتوقع الجديد بصيغة YYYY-MM-DDTHH:mm', current)
    if (promisedAt === null) return
    await update(`/workshop/job-cards/${jobCard.id}/reschedule/`, { promised_at: promisedAt || null }, 'تم تحديث موعد التسليم المتوقع وظهر التحديث في رابط العميل.')
  }

  const reviewPartRequest = async (id, action) => {
    setError('')
    try {
      await api.post(`/inventory/part-requests/${id}/${action}/`)
      await refresh()
      setNotice(action === 'fulfill' ? 'تم صرف القطعة وتحديث المخزون.' : action === 'approve' ? 'تم اعتماد طلب القطعة.' : 'تم رفض طلب القطعة.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر معالجة طلب القطعة.'))
    }
  }

  const acknowledgeAlert = async (id) => {
    setError('')
    try {
      await api.post(`/inventory/alerts/${id}/acknowledge/`)
      await refresh()
      setNotice('تم تأكيد تنبيه المخزون.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر تأكيد التنبيه.'))
    }
  }

  const updateTask = async (id, action) => {
    setError('')
    try {
      await api.post(`/workforce/tasks/${id}/${action}/`)
      await refresh()
      setNotice(action === 'start' ? 'تم بدء المهمة.' : 'تم إكمال المهمة وتسجيل الوقت.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر تحديث المهمة.'))
    }
  }

  const generateCommissions = async () => {
    setError('')
    try {
      const now = new Date()
      await api.post('/workforce/commissions/generate/', { year: now.getFullYear(), month: now.getMonth() + 1 })
      await refresh()
      setNotice('تم احتساب عمولات الشهر الحالي.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر احتساب العمولات.'))
    }
  }

  const createInvoice = async (jobCard) => {
    setError('')
    try {
      await api.post('/accounting/invoices/create-from-job/', { job_card: jobCard })
      await refresh()
      setNotice('تم إنشاء مسودة الفاتورة من خدمات وقطع بطاقة العمل.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر إنشاء الفاتورة.'))
    }
  }

  const generateInvoicePdf = async (invoiceId) => {
    setError('')
    try {
      const { data } = await api.post(`/accounting/invoices/${invoiceId}/generate_pdf/`)
      const pdf = await api.get(`/accounting/invoices/${invoiceId}/download-pdf/`, { responseType: 'blob' })
      const objectUrl = URL.createObjectURL(pdf.data)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = `${data.invoice_number}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(objectUrl)
      await refresh()
      setNotice('تم توليد وتنزيل ملف PDF للفاتورة.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر توليد ملف الفاتورة.'))
    }
  }

  const recordPayment = async (invoiceId, amount, method = 'cash', reference = '') => {
    setError('')
    try {
      await api.post(`/accounting/invoices/${invoiceId}/record-payment/`, { amount, method, reference })
      await refresh()
      setNotice('تم تسجيل الدفعة وتحديث حالة الفاتورة.')
      return true
    } catch (requestError) {
      setError(getError(requestError, 'تعذر تسجيل الدفعة.'))
      return false
    }
  }

  const copyPortalLink = async (jobCardId) => {
    setError('')
    try {
      const { data } = await api.get(`/workshop/job-cards/${jobCardId}/portal-link/`)
      await navigator.clipboard.writeText(data.url)
      setNotice('تم نسخ رابط متابعة العميل. يمكنك إرساله عبر أي قناة تواصل.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر إنشاء رابط المتابعة.'))
    }
  }

  const uploadDocument = async (formData) => {
    setError('')
    try {
      await api.post('/documents/documents/', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      await refresh()
      setNotice('تم رفع الوثيقة وتشفيرها بنجاح.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر رفع الوثيقة.'))
    }
  }

  const downloadDocument = async (document) => {
    setError('')
    try {
      const response = await api.get(`/documents/documents/${document.id}/download/`, { responseType: 'blob' })
      const url = URL.createObjectURL(response.data)
      const link = window.document.createElement('a')
      link.href = url
      link.download = document.original_filename
      link.click()
      URL.revokeObjectURL(url)
    } catch (requestError) {
      setError(getError(requestError, 'تعذر تنزيل الوثيقة.'))
    }
  }

  const acknowledgeDocumentAlert = async (id) => {
    setError('')
    try {
      await api.post(`/documents/alerts/${id}/acknowledge/`)
      await refresh()
      setNotice('تم تأكيد الاطلاع على تنبيه الوثيقة.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر تأكيد التنبيه.'))
    }
  }

  const saveWorkshopProfile = async (event) => {
    event.preventDefault()
    setError('')
    setNotice('')
    const formData = new FormData()
    Object.entries(workshopProfile).forEach(([key, value]) => {
      if (key !== 'logo_url' && key !== 'logo' && value !== null && value !== undefined) formData.append(key, value)
    })
    if (workshopLogo) formData.append('logo', workshopLogo)
    try {
      const { data } = await api.patch('/auth/workshop/', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      setWorkshopProfile({ ...emptyWorkshopProfile, ...data })
      setWorkshopLogo(null)
      setNotice('تم حفظ بيانات الورشة المعتمدة للفواتير.')
    } catch (requestError) {
      setError(getError(requestError, 'تعذر حفظ إعدادات الورشة.'))
    }
  }

  const navItems = [['dashboard', user.role === 'technician' ? 'لوحة المهام' : 'لوحة الملخص'], ['jobs', user.role === 'technician' ? 'مهامي' : 'بطاقات العمل']]
  if (isManager || user.role === 'technician') navItems.push(['tasks', user.role === 'technician' ? 'مهامي التفصيلية' : 'المهام'])
  if (isManager) navItems.push(['customers', 'العملاء'], ['vehicles', 'المركبات'])
  if (isManager) navItems.push(['services', 'الخدمات'])
  if (canUseInventory) navItems.push(['inventory', user.role === 'technician' ? 'طلبات قطع الغيار' : 'المخزون'])
  if (isManager) navItems.push(['employees', 'الموظفون'])
  if (isFinancial) navItems.push(['commissions', 'العمولات'], ['accounting', 'المحاسبة'], ['pos', 'نقطة البيع'])
  if (isManager) navItems.push(['documents', 'الوثائق'], ['team', 'فريق العمل'])
  navItems.push(['support', 'حول عزم والدعم'])

  if (isOwner) navItems.splice(navItems.length - 1, 0, ['workshop-settings', 'إعدادات الورشة'])

  const selectedValues = (event) => Array.from(event.target.selectedOptions, (option) => Number(option.value))
  const availableVehicles = job.customer ? vehicles.filter((item) => item.customer === Number(job.customer)) : vehicles
  const saveSupplier = async (event) => {
    if (!supplier.id) return submit(event, '/inventory/suppliers/', supplier, () => setSupplier(emptySupplier), 'تمت إضافة المورد.')
    event.preventDefault()
    if (await update(`/inventory/suppliers/${supplier.id}/`, supplier, 'تم تحديث بيانات المورد.')) setSupplier(emptySupplier)
  }

  return <main className="workspace" dir={language === 'ar' ? 'rtl' : 'ltr'} ref={contentRef}>
    <WorkspaceNavigation user={user} navItems={navItems} view={view} onSelect={setView} onLogout={onLogout} />
    <section className="workspace-content">
      <WorkspaceHeader user={user} title={navItems.find(([id]) => id === view)?.[1]} language={language} onLanguageChange={onLanguageChange} />
      {notice && <p className="feedback success" role="status">{notice}</p>}{error && <p className="feedback error" role="alert">{error}</p>}
      {loading ? <p className="empty-state">جارٍ تحميل البيانات...</p> : <>
        {view === 'dashboard' && <DashboardPage dashboard={dashboard} jobs={jobs} onStatus={updateJobStatus} isTechnician={user.role === 'technician'} canChangeStatus={isOperational || user.role === 'technician'} canDeliver={isOperational} onDeliver={deliverJob} onReschedule={rescheduleJob} />}
        {view === 'jobs' && <JobsPage jobs={jobs} isManager={isOperational} customers={customers} vehicles={availableVehicles} services={services} team={team} job={job} setJob={setJob} selectedValues={selectedValues} onSubmit={(event) => submit(event, '/workshop/job-cards/', { ...job, promised_at: job.promised_at || null }, () => setJob(emptyJob), 'تم فتح بطاقة العمل.')} onStatus={updateJobStatus} onPortalLink={copyPortalLink} canChangeStatus={isOperational || user.role === 'technician'} canDeliver={isOperational} onDeliver={deliverJob} onReschedule={rescheduleJob} />}
        {view === 'tasks' && <TasksPage tasks={tasks} isManager={isManager} jobs={jobs} employees={employees} task={task} setTask={setTask} onSubmit={(event) => submit(event, '/workforce/tasks/', task, () => setTask(emptyTask), 'تم إنشاء المهمة وإسنادها للفني.')} onTaskAction={updateTask} />}
        {isManager && view === 'customers' && <RecordsPage title="العملاء" form={<form className="entry-form" onSubmit={(event) => submit(event, '/workshop/customers/', customer, () => setCustomer(emptyCustomer), 'تمت إضافة العميل.')}><label>الاسم<input required value={customer.name} onChange={(e) => setCustomer({ ...customer, name: e.target.value })} /></label><label>الهاتف<input required value={customer.phone} onChange={(e) => setCustomer({ ...customer, phone: e.target.value })} /></label><label>البريد<input type="email" value={customer.email} onChange={(e) => setCustomer({ ...customer, email: e.target.value })} /></label><label className="wide">ملاحظات<textarea value={customer.notes} onChange={(e) => setCustomer({ ...customer, notes: e.target.value })} /></label><button className="primary">إضافة العميل</button></form>} items={customers} columns={(item) => <><strong>{item.name}</strong><span>{item.phone}</span><span>{item.email || '—'}</span></>} onDelete={(id) => remove('/workshop/customers/', id)} />}
        {isManager && view === 'vehicles' && <RecordsPage title="المركبات" form={<form className="entry-form" onSubmit={(event) => submit(event, '/workshop/vehicles/', { ...vehicle, model_year: vehicle.model_year || null, mileage: vehicle.mileage || null }, () => setVehicle(emptyVehicle), 'تمت إضافة المركبة.')}><label>العميل<select required value={vehicle.customer} onChange={(e) => setVehicle({ ...vehicle, customer: e.target.value })}><option value="">اختر العميل</option>{customers.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>رقم اللوحة<input required value={vehicle.license_plate} onChange={(e) => setVehicle({ ...vehicle, license_plate: e.target.value })} /></label><label>الشركة<input required value={vehicle.make} onChange={(e) => setVehicle({ ...vehicle, make: e.target.value })} /></label><label>الموديل<input required value={vehicle.model} onChange={(e) => setVehicle({ ...vehicle, model: e.target.value })} /></label><label>سنة الصنع<input type="number" value={vehicle.model_year} onChange={(e) => setVehicle({ ...vehicle, model_year: e.target.value })} /></label><label>رقم الهيكل<input value={vehicle.vin} onChange={(e) => setVehicle({ ...vehicle, vin: e.target.value })} /></label><button className="primary">إضافة المركبة</button></form>} items={vehicles} columns={(item) => <><strong>{item.license_plate}</strong><span>{item.make} {item.model}</span><span>{item.customer_name}</span></>} onDelete={(id) => remove('/workshop/vehicles/', id)} />}
        {isManager && view === 'services' && <RecordsPage title="الخدمات" form={<form className="entry-form" onSubmit={(event) => submit(event, '/workshop/services/', service, () => setService(emptyService), 'تمت إضافة الخدمة.')}><label>اسم الخدمة<input required value={service.name} onChange={(e) => setService({ ...service, name: e.target.value })} /></label><label>السعر الأساسي<input required type="number" min="0" step="0.01" value={service.base_price} onChange={(e) => setService({ ...service, base_price: e.target.value })} /></label><label className="wide">الوصف<textarea value={service.description} onChange={(e) => setService({ ...service, description: e.target.value })} /></label><button className="primary">إضافة الخدمة</button></form>} items={services} columns={(item) => <><strong>{item.name}</strong><span>{item.description || '—'}</span><span>{item.base_price} ر.س</span></>} onDelete={(id) => remove('/workshop/services/', id)} />}
        {canUseInventory && view === 'inventory' && <InventoryPage suppliers={suppliers} parts={parts} lowStock={lowStock} alerts={alerts} partUsages={partUsages} partRequests={partRequests} jobs={jobs} supplier={supplier} setSupplier={setSupplier} part={part} setPart={setPart} partUsage={partUsage} setPartUsage={setPartUsage} partRequest={partRequest} setPartRequest={setPartRequest} onSaveSupplier={saveSupplier} onCancelSupplier={() => setSupplier(emptySupplier)} onSubmitPart={(event) => submit(event, '/inventory/parts/', { ...part, supplier: part.supplier || null }, () => setPart(emptyPart), 'تمت إضافة قطعة الغيار.')} onSubmitUsage={(event) => submit(event, '/inventory/part-usages/', partUsage, () => setPartUsage(emptyPartUsage), 'تم صرف القطعة وتحديث المخزون.')} onSubmitRequest={(event) => submit(event, '/inventory/part-requests/', partRequest, () => setPartRequest(emptyPartRequest), 'تم إرسال طلب القطعة للمخزن.')} onDeleteSupplier={(id) => remove('/inventory/suppliers/', id)} onDeletePart={(id) => remove('/inventory/parts/', id)} onAcknowledge={acknowledgeAlert} onReviewRequest={reviewPartRequest} canManage={canManageInventory} canIssue={canIssueParts} isTechnician={user.role === 'technician'} />}
        {isManager && view === 'employees' && <EmployeesPage employees={employees} team={team} employee={employee} setEmployee={setEmployee} onSubmit={(event) => submit(event, '/workforce/employees/', employee, () => setEmployee(emptyEmployee), 'تم إنشاء ملف الموظف.')} onDelete={(id) => remove('/workforce/employees/', id)} />}
        {isFinancial && view === 'commissions' && <CommissionsPage commissions={commissions} onGenerate={generateCommissions} />}
        {isFinancial && view === 'accounting' && <AccountingPage jobs={jobs} invoices={invoices} expenses={expenses} vouchers={vouchers} profitLoss={profitLoss} expense={expense} setExpense={setExpense} voucher={voucher} setVoucher={setVoucher} submit={submit} update={update} onCreateInvoice={createInvoice} onGeneratePdf={generateInvoicePdf} onRecordPayment={recordPayment} remove={remove} />}
        {isFinancial && view === 'pos' && <PointOfSalePage invoices={invoices} onRecordPayment={recordPayment} />}
        {isManager && view === 'documents' && <DocumentsPage documents={documents} alerts={documentAlerts} customers={customers} vehicles={vehicles} employees={employees} onUpload={uploadDocument} onDownload={downloadDocument} onAcknowledge={acknowledgeDocumentAlert} remove={remove} />}
        {isManager && view === 'team' && <RecordsPage title="الفريق" form={<form className="entry-form" onSubmit={(event) => submit(event, '/auth/team/', teamMember, () => setTeamMember(emptyTeamMember), 'تمت إضافة عضو الفريق.')}><label>الاسم الأول<input required value={teamMember.first_name} onChange={(e) => setTeamMember({ ...teamMember, first_name: e.target.value })} /></label><label>اسم العائلة<input required value={teamMember.last_name} onChange={(e) => setTeamMember({ ...teamMember, last_name: e.target.value })} /></label><label>اسم المستخدم<input required value={teamMember.username} onChange={(e) => setTeamMember({ ...teamMember, username: e.target.value })} /></label><label>كلمة المرور<input required minLength="8" type="password" value={teamMember.password} onChange={(e) => setTeamMember({ ...teamMember, password: e.target.value })} /></label><label>الدور<select value={teamMember.role} onChange={(e) => setTeamMember({ ...teamMember, role: e.target.value })}><option value="technician">فني</option><option value="accountant">محاسب</option><option value="receptionist">موظف استقبال</option><option value="storekeeper">أمين مخزن</option><option value="manager">مدير</option></select></label><button className="primary">إضافة عضو</button></form>} items={team} columns={(item) => <><strong>{item.first_name} {item.last_name}</strong><span>{item.username}</span><span>{{ manager: 'مدير', technician: 'فني', accountant: 'محاسب', receptionist: 'موظف استقبال', storekeeper: 'أمين مخزن' }[item.role] || item.role}</span></>} />}
        {isOwner && view === 'workshop-settings' && <WorkshopSettingsPage profile={workshopProfile} setProfile={setWorkshopProfile} logo={workshopLogo} setLogo={setWorkshopLogo} onSubmit={saveWorkshopProfile} />}
        {view === 'support' && <AboutSupport />}
      </>}
    </section>
  </main>
}

function AboutSupport() {
  return <section className="about-support">
    <div className="about-hero"><span className="eyebrow">AZM</span><h2>عزم لإدارة ورش السيارات</h2><p>منصة موحدة تساعد الورش على إدارة بطاقات العمل والعملاء والمخزون والمحاسبة والفريق من مكان واحد.</p></div>
    <div className="about-grid">
      <article><h3>عن البرنامج</h3><p>صُمم عزم ليربط سير العمل اليومي في الورشة ببيانات منظمة وصلاحيات واضحة وتحديثات فورية.</p><ul><li>إدارة بطاقات العمل والعملاء والمركبات والخدمات.</li><li>مخزون وقطع غيار ومحاسبة ونقطة بيع.</li><li>مهام الفنيين، أرشفة الوثائق وتنبيهات المتابعة.</li></ul></article>
      <article><h3>الهوية</h3><p>تعكس هوية عزم القوة والموثوقية والاحترافية التقنية في قطاع صيانة السيارات.</p><ul><li>شعار مستلهم من الترس الميكانيكي والمكبس.</li><li>الأزرق العميق للثقة والتقنية، والفضي لطابع المعدن والصلابة.</li><li>واجهات واضحة وسهلة القراءة للعمل اليومي.</li></ul></article>
    </div>
    <section className="support-card"><div><span className="eyebrow">الدعم الفني</span><h2>نحن هنا لمساعدتك</h2><p>للمساعدة في الاستخدام أو الدعم الفني، تواصل مباشرة مع مسؤول الدعم.</p></div><div className="support-contact"><strong>طارق حسين صالح (أبو سجاد)</strong><a href="mailto:thsedahmed@gmail.com">thsedahmed@gmail.com</a><a href="mailto:thsedahmed@hotmail.com">thsedahmed@hotmail.com</a></div></section>
  </section>
}

export default Workspace
