import { useCallback, useEffect, useRef, useState } from 'react'
import api from './api'
import { useLocalizedContent } from './i18n.js'
import LanguageToggle from './LanguageToggle.jsx'
import azmLogo from '../../azm_logo.png'

const statusLabels = { pending: 'بانتظار الفحص', in_progress: 'قيد الإصلاح', ready: 'جاهزة للاستلام', delivered: 'تم التسليم', cancelled: 'ملغاة' }
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
const emptyExpense = { category: 'other', description: '', amount: '', occurred_at: today, reference: '' }
const emptyVoucher = { voucher_type: 'receipt', amount: '', party_name: '', description: '', reference: '', occurred_at: today, invoice: '', payment_method: 'cash', category: 'other' }
const emptyWorkshopProfile = { name: '', legal_name: '', tax_number: '', commercial_registration: '', phone: '', email: '', website: '', city: '', district: '', street: '', building_number: '', postal_code: '', additional_number: '', national_address: '', latitude: '', longitude: '', auto_deliver_paid_ready_jobs: false, logo_url: '' }

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
  if (isManager) navItems.push(['documents', 'الوثائق'], ['team', 'الحسابات'])
  navItems.push(['support', 'حول عزم والدعم'])

  if (isOwner) navItems.splice(navItems.length - 1, 0, ['workshop-settings', 'إعدادات الورشة'])

  const selectedValues = (event) => Array.from(event.target.selectedOptions, (option) => Number(option.value))
  const availableVehicles = job.customer ? vehicles.filter((item) => item.customer === Number(job.customer)) : vehicles

  return <main className="workspace" dir={language === 'ar' ? 'rtl' : 'ltr'} ref={contentRef}>
    <aside className="side-nav"><div className="brand-mini"><img src={azmLogo} alt="Azm logo" /></div><p>{user.workshop?.name}</p>{navItems.map(([id, label]) => <button type="button" key={id} className={view === id ? 'nav-active' : ''} onClick={() => setView(id)}>{label}</button>)}<button type="button" className="nav-logout" onClick={onLogout}>تسجيل الخروج</button></aside>
    <section className="workspace-content">
      <header className="workspace-header"><div><span className="eyebrow">إدارة الورشة</span><h1>{navItems.find(([id]) => id === view)?.[1]}</h1></div><div className="header-actions"><LanguageToggle language={language} onChange={onLanguageChange} compact /><div className="user-chip">{user.first_name || user.username}<small>{{ owner: 'مالك الورشة', manager: 'مدير الورشة', accountant: 'محاسب', technician: 'فني', receptionist: 'موظف استقبال', storekeeper: 'أمين مخزن' }[user.role] || user.role}</small></div></div></header>
      {notice && <p className="feedback success" role="status">{notice}</p>}{error && <p className="feedback error" role="alert">{error}</p>}
      {loading ? <p className="empty-state">جارٍ تحميل البيانات...</p> : <>
        {view === 'dashboard' && <Dashboard dashboard={dashboard} jobs={jobs} onStatus={updateJobStatus} isTechnician={user.role === 'technician'} canChangeStatus={isOperational || user.role === 'technician'} canDeliver={isOperational} onDeliver={deliverJob} onReschedule={rescheduleJob} />}
        {view === 'jobs' && <Jobs jobs={jobs} isManager={isOperational} customers={customers} vehicles={availableVehicles} services={services} team={team} job={job} setJob={setJob} selectedValues={selectedValues} onSubmit={(event) => submit(event, '/workshop/job-cards/', { ...job, promised_at: job.promised_at || null }, () => setJob(emptyJob), 'تم فتح بطاقة العمل.')} onStatus={updateJobStatus} onPortalLink={copyPortalLink} canChangeStatus={isOperational || user.role === 'technician'} canDeliver={isOperational} onDeliver={deliverJob} onReschedule={rescheduleJob} />}
        {view === 'tasks' && <Tasks tasks={tasks} isManager={isManager} jobs={jobs} employees={employees} task={task} setTask={setTask} submit={submit} onTaskAction={updateTask} />}
        {isManager && view === 'customers' && <Records title="العملاء" form={<form className="entry-form" onSubmit={(event) => submit(event, '/workshop/customers/', customer, () => setCustomer(emptyCustomer), 'تمت إضافة العميل.')}><label>الاسم<input required value={customer.name} onChange={(e) => setCustomer({ ...customer, name: e.target.value })} /></label><label>الهاتف<input required value={customer.phone} onChange={(e) => setCustomer({ ...customer, phone: e.target.value })} /></label><label>البريد<input type="email" value={customer.email} onChange={(e) => setCustomer({ ...customer, email: e.target.value })} /></label><label className="wide">ملاحظات<textarea value={customer.notes} onChange={(e) => setCustomer({ ...customer, notes: e.target.value })} /></label><button className="primary">إضافة العميل</button></form>} items={customers} columns={(item) => <><strong>{item.name}</strong><span>{item.phone}</span><span>{item.email || '—'}</span></>} onDelete={(id) => remove('/workshop/customers/', id)} />}
        {isManager && view === 'vehicles' && <Records title="المركبات" form={<form className="entry-form" onSubmit={(event) => submit(event, '/workshop/vehicles/', { ...vehicle, model_year: vehicle.model_year || null, mileage: vehicle.mileage || null }, () => setVehicle(emptyVehicle), 'تمت إضافة المركبة.')}><label>العميل<select required value={vehicle.customer} onChange={(e) => setVehicle({ ...vehicle, customer: e.target.value })}><option value="">اختر العميل</option>{customers.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>رقم اللوحة<input required value={vehicle.license_plate} onChange={(e) => setVehicle({ ...vehicle, license_plate: e.target.value })} /></label><label>الشركة<input required value={vehicle.make} onChange={(e) => setVehicle({ ...vehicle, make: e.target.value })} /></label><label>الموديل<input required value={vehicle.model} onChange={(e) => setVehicle({ ...vehicle, model: e.target.value })} /></label><label>سنة الصنع<input type="number" value={vehicle.model_year} onChange={(e) => setVehicle({ ...vehicle, model_year: e.target.value })} /></label><label>رقم الهيكل<input value={vehicle.vin} onChange={(e) => setVehicle({ ...vehicle, vin: e.target.value })} /></label><button className="primary">إضافة المركبة</button></form>} items={vehicles} columns={(item) => <><strong>{item.license_plate}</strong><span>{item.make} {item.model}</span><span>{item.customer_name}</span></>} onDelete={(id) => remove('/workshop/vehicles/', id)} />}
        {isManager && view === 'services' && <Records title="الخدمات" form={<form className="entry-form" onSubmit={(event) => submit(event, '/workshop/services/', service, () => setService(emptyService), 'تمت إضافة الخدمة.')}><label>اسم الخدمة<input required value={service.name} onChange={(e) => setService({ ...service, name: e.target.value })} /></label><label>السعر الأساسي<input required type="number" min="0" step="0.01" value={service.base_price} onChange={(e) => setService({ ...service, base_price: e.target.value })} /></label><label className="wide">الوصف<textarea value={service.description} onChange={(e) => setService({ ...service, description: e.target.value })} /></label><button className="primary">إضافة الخدمة</button></form>} items={services} columns={(item) => <><strong>{item.name}</strong><span>{item.description || '—'}</span><span>{item.base_price} ر.س</span></>} onDelete={(id) => remove('/workshop/services/', id)} />}
        {canUseInventory && view === 'inventory' && <Inventory suppliers={suppliers} parts={parts} lowStock={lowStock} alerts={alerts} partUsages={partUsages} partRequests={partRequests} jobs={jobs} supplier={supplier} setSupplier={setSupplier} part={part} setPart={setPart} partUsage={partUsage} setPartUsage={setPartUsage} partRequest={partRequest} setPartRequest={setPartRequest} submit={submit} update={update} remove={remove} onAcknowledge={acknowledgeAlert} onReviewRequest={reviewPartRequest} canManage={canManageInventory} canIssue={canIssueParts} isTechnician={user.role === 'technician'} />}
        {isManager && view === 'employees' && <Employees employees={employees} team={team} employee={employee} setEmployee={setEmployee} submit={submit} remove={remove} />}
        {isFinancial && view === 'commissions' && <Commissions commissions={commissions} onGenerate={generateCommissions} />}
        {isFinancial && view === 'accounting' && <Accounting jobs={jobs} invoices={invoices} expenses={expenses} vouchers={vouchers} profitLoss={profitLoss} expense={expense} setExpense={setExpense} voucher={voucher} setVoucher={setVoucher} submit={submit} update={update} onCreateInvoice={createInvoice} onGeneratePdf={generateInvoicePdf} onRecordPayment={recordPayment} remove={remove} />}
        {isFinancial && view === 'pos' && <PointOfSale invoices={invoices} onRecordPayment={recordPayment} />}
        {isManager && view === 'documents' && <Documents documents={documents} alerts={documentAlerts} customers={customers} vehicles={vehicles} employees={employees} onUpload={uploadDocument} onDownload={downloadDocument} onAcknowledge={acknowledgeDocumentAlert} remove={remove} />}
        {isManager && view === 'team' && <Records title="الفريق" form={<form className="entry-form" onSubmit={(event) => submit(event, '/auth/team/', teamMember, () => setTeamMember(emptyTeamMember), 'تمت إضافة عضو الفريق.')}><label>الاسم الأول<input required value={teamMember.first_name} onChange={(e) => setTeamMember({ ...teamMember, first_name: e.target.value })} /></label><label>اسم العائلة<input required value={teamMember.last_name} onChange={(e) => setTeamMember({ ...teamMember, last_name: e.target.value })} /></label><label>اسم المستخدم<input required value={teamMember.username} onChange={(e) => setTeamMember({ ...teamMember, username: e.target.value })} /></label><label>كلمة المرور<input required minLength="8" type="password" value={teamMember.password} onChange={(e) => setTeamMember({ ...teamMember, password: e.target.value })} /></label><label>الدور<select value={teamMember.role} onChange={(e) => setTeamMember({ ...teamMember, role: e.target.value })}><option value="technician">فني</option><option value="accountant">محاسب</option><option value="receptionist">موظف استقبال</option><option value="storekeeper">أمين مخزن</option><option value="manager">مدير</option></select></label><button className="primary">إضافة عضو</button></form>} items={team} columns={(item) => <><strong>{item.first_name} {item.last_name}</strong><span>{item.username}</span><span>{{ manager: 'مدير', technician: 'فني', accountant: 'محاسب', receptionist: 'موظف استقبال', storekeeper: 'أمين مخزن' }[item.role] || item.role}</span></>} />}
        {isOwner && view === 'workshop-settings' && <WorkshopSettings profile={workshopProfile} setProfile={setWorkshopProfile} logo={workshopLogo} setLogo={setWorkshopLogo} onSubmit={saveWorkshopProfile} />}
        {view === 'support' && <AboutSupport />}
      </>}
    </section>
  </main>
}

function WorkshopSettings({ profile, setProfile, logo, setLogo, onSubmit }) {
  const change = (key) => (event) => setProfile({ ...profile, [key]: event.target.value })
  return <section className="form-card workshop-settings">
    <div className="section-heading"><div><h2>هوية وبيانات الورشة</h2><p>تظهر هذه البيانات في الفواتير الضريبية. التعديل متاح لمالك الورشة فقط.</p></div>{profile.logo_url && <img className="workshop-logo-preview" src={profile.logo_url} alt="شعار الورشة" />}</div>
    <form className="entry-form" onSubmit={onSubmit}>
      <label>اسم الورشة<input required value={profile.name} onChange={change('name')} /></label>
      <label>الاسم القانوني<input required value={profile.legal_name} onChange={change('legal_name')} /></label>
      <label>الرقم الضريبي<input required inputMode="numeric" pattern="[0-9]{15}" minLength="15" maxLength="15" value={profile.tax_number} onChange={change('tax_number')} title="يجب أن يتكون الرقم الضريبي من 15 رقماً" /></label>
      <label>السجل التجاري<input value={profile.commercial_registration} onChange={change('commercial_registration')} /></label>
      <label>رقم الاتصال<input required type="tel" value={profile.phone} onChange={change('phone')} /></label>
      <label>البريد الإلكتروني<input type="email" value={profile.email} onChange={change('email')} /></label>
      <label>الموقع الإلكتروني<input type="url" placeholder="https://" value={profile.website} onChange={change('website')} /></label>
      <label>المدينة<input required value={profile.city} onChange={change('city')} /></label>
      <label>الحي<input required value={profile.district} onChange={change('district')} /></label>
      <label>الشارع<input required value={profile.street} onChange={change('street')} /></label>
      <label>رقم المبنى<input required value={profile.building_number} onChange={change('building_number')} /></label>
      <label>الرمز البريدي<input required inputMode="numeric" value={profile.postal_code} onChange={change('postal_code')} /></label>
      <label>الرقم الإضافي<input value={profile.additional_number} onChange={change('additional_number')} /></label>
      <label className="wide"><input type="checkbox" checked={Boolean(profile.auto_deliver_paid_ready_jobs)} onChange={(event) => setProfile({ ...profile, auto_deliver_paid_ready_jobs: event.target.checked })} /> تسليم البطاقة الجاهزة آليًا عند سداد الفاتورة بالكامل</label>
      <label>خط العرض<input type="number" min="-90" max="90" step="0.000001" value={profile.latitude} onChange={change('latitude')} /></label>
      <label>خط الطول<input type="number" min="-180" max="180" step="0.000001" value={profile.longitude} onChange={change('longitude')} /></label>
      <label className="wide">العنوان الوطني<textarea value={profile.national_address} onChange={change('national_address')} placeholder="يمكن إضافة وصف العنوان الوطني كاملاً" /></label>
      <label className="wide">شعار الورشة (PNG أو JPG، بحد أقصى 2MB)<input accept="image/png,image/jpeg,image/webp" type="file" onChange={(event) => setLogo(event.target.files?.[0] || null)} />{logo && <small>{logo.name}</small>}</label>
      <button className="primary">حفظ إعدادات الورشة</button>
    </form>
  </section>
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

function Dashboard({ dashboard, jobs, onStatus, isTechnician, canChangeStatus, canDeliver, onDeliver, onReschedule }) {
  return <><section className="dashboard-intro"><div><h2>{isTechnician ? 'مهامك المسندة' : 'ملخص بطاقات العمل'}</h2><p>تتحدث هذه البيانات مباشرة من قاعدة الورشة.</p></div></section><section className="status-grid">{Object.entries(statusLabels).map(([key, label]) => <article className={`status-card ${key}`} key={key}><span>{label}</span><strong>{dashboard?.counts?.[key] ?? 0}</strong></article>)}</section><JobList jobs={jobs.slice(0, 5)} onStatus={onStatus} isManager={canDeliver} canChangeStatus={canChangeStatus} canDeliver={canDeliver} onDeliver={onDeliver} onReschedule={onReschedule} /></>
}

function Jobs({ jobs, isManager, customers, vehicles, services, team, job, setJob, selectedValues, onSubmit, onStatus, onPortalLink, canChangeStatus, canDeliver, onDeliver, onReschedule }) {
  return <><section className="dashboard-intro"><div><h2>{isManager ? 'بطاقات العمل' : 'مهامي'}</h2><p>{isManager ? 'افتح بطاقة جديدة، وحدد العميل والمركبة والفنيين.' : 'تابع البطاقات المتاحة حسب صلاحيات حسابك.'}</p></div></section>{isManager && <form className="entry-form job-form" onSubmit={onSubmit}><label>العميل<select required value={job.customer} onChange={(e) => setJob({ ...job, customer: e.target.value, vehicle: '' })}><option value="">اختر العميل</option>{customers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>المركبة<select required value={job.vehicle} onChange={(e) => setJob({ ...job, vehicle: e.target.value })}><option value="">اختر المركبة</option>{vehicles.map((item) => <option key={item.id} value={item.id}>{item.license_plate} — {item.make} {item.model}</option>)}</select></label><label>الخدمات<select multiple value={job.service_ids} onChange={(e) => setJob({ ...job, service_ids: selectedValues(e) })}>{services.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>الفنيون<select multiple value={job.technician_ids} onChange={(e) => setJob({ ...job, technician_ids: selectedValues(e) })}>{team.filter((item) => item.role === 'technician').map((item) => <option key={item.id} value={item.id}>{item.first_name || item.username}</option>)}</select></label><label>التكلفة التقديرية<input type="number" min="0" step="0.01" value={job.estimated_cost} onChange={(e) => setJob({ ...job, estimated_cost: e.target.value })} /></label><label>موعد الإنجاز<input type="datetime-local" value={job.promised_at} onChange={(e) => setJob({ ...job, promised_at: e.target.value })} /></label><label className="wide">وصف العطل<textarea required value={job.complaint} onChange={(e) => setJob({ ...job, complaint: e.target.value })} /></label><label className="wide">نتيجة الفحص (اختياري)<textarea value={job.diagnosis} onChange={(e) => setJob({ ...job, diagnosis: e.target.value })} /></label><button className="primary">فتح بطاقة عمل</button></form>}<JobList jobs={jobs} onStatus={onStatus} isManager={isManager} onPortalLink={onPortalLink} canChangeStatus={canChangeStatus} canDeliver={canDeliver} onDeliver={onDeliver} onReschedule={onReschedule} /></>
}

function JobList({ jobs, onStatus, isManager, onPortalLink, canChangeStatus, canDeliver, onDeliver, onReschedule }) {
  const formatDate = (value) => value ? new Date(value).toLocaleString('ar-SA') : 'غير محدد'
  return <section className="recent-jobs"><div className="section-heading"><h2>البطاقات</h2><span>{jobs.length} بطاقة</span></div>{jobs.length ? <div className="job-table"><div className="job-row job-head"><span>البطاقة</span><span>المركبة والعميل</span><span>العطل والموعد</span><span>الحالة</span></div>{jobs.map((item) => <div className="job-row" key={item.id}><strong>{item.job_number}</strong><span>{item.vehicle_label}<small>{item.customer_name}</small></span><span>{item.complaint}<small>التسليم المتوقع: {formatDate(item.promised_at)}</small>{item.promised_at && new Date(item.promised_at) < new Date() && !['ready', 'delivered', 'cancelled'].includes(item.status) && <small className="overdue">متأخرة عن الموعد</small>}</span><span><span className={`job-status ${item.status}`}>{item.status_label}</span>{canChangeStatus && item.status === 'pending' && <button className="text-action" type="button" onClick={() => onStatus(item.id, 'in_progress')}>بدء العمل</button>}{canChangeStatus && item.status === 'in_progress' && <button className="text-action" type="button" onClick={() => onStatus(item.id, 'ready')}>جاهزة للتسليم</button>}{canDeliver && item.status === 'ready' && <button className="text-action" type="button" onClick={() => onDeliver(item.id)}>تسليم للعميل</button>}{isManager && !['delivered', 'cancelled'].includes(item.status) && <button className="text-action" type="button" onClick={() => onReschedule(item)}>تحديث الموعد</button>}{isManager && onPortalLink && <button className="text-action" type="button" onClick={() => onPortalLink(item.id)}>رابط العميل</button>}</span></div>)}</div> : <p className="empty-state">لا توجد بطاقات عمل حالياً.</p>}</section>
}

function Tasks({ tasks, isManager, jobs, employees, task, setTask, submit, onTaskAction }) {
  return <><section className="dashboard-intro"><div><h2>{isManager ? 'مهام الفريق' : 'مهامي التفصيلية'}</h2><p>{isManager ? 'أنشئ مهمة مستقلة لكل فني في بطاقة العمل.' : 'ابدأ المهمة ثم أكملها لتسجيل الوقت واحتساب العمولة.'}</p></div></section>
    {isManager && <section className="form-card"><form className="entry-form" onSubmit={(event) => submit(event, '/workforce/tasks/', task, () => setTask(emptyTask), 'تم إنشاء المهمة وإسنادها للفني.')}><label>بطاقة العمل<select required value={task.job_card} onChange={(e) => setTask({ ...task, job_card: e.target.value })}><option value="">اختر البطاقة</option>{jobs.map((item) => <option key={item.id} value={item.id}>{item.job_number} — {item.vehicle_label}</option>)}</select></label><label>الفني<select required value={task.employee} onChange={(e) => setTask({ ...task, employee: e.target.value })}><option value="">اختر الفني</option>{employees.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.user_name} — {item.job_title}</option>)}</select></label><label>اسم المهمة<input required value={task.title} onChange={(e) => setTask({ ...task, title: e.target.value })} /></label><label>الساعات التقديرية<input required type="number" min="0" step="0.25" value={task.estimated_hours} onChange={(e) => setTask({ ...task, estimated_hours: e.target.value })} /></label><label className="wide">الوصف<textarea value={task.description} onChange={(e) => setTask({ ...task, description: e.target.value })} /></label><button className="primary">إسناد المهمة</button></form></section>}
    <section className="recent-jobs"><div className="section-heading"><h2>المهام</h2><span>{tasks.length} مهمة</span></div>{tasks.length ? <div className="record-list">{tasks.map((item) => <div className="task-row" key={item.id}><div><strong>{item.title}</strong><small>{item.job_number} · {item.employee_name || 'فني'}</small></div><span className={`job-status ${item.status}`}>{item.status_label}</span><span>{item.actual_minutes} دقيقة</span><span>{item.status === 'not_started' && <button className="text-action" type="button" onClick={() => onTaskAction(item.id, 'start')}>بدء</button>}{item.status === 'in_progress' && <button className="text-action" type="button" onClick={() => onTaskAction(item.id, 'complete')}>إكمال</button>}</span></div>)}</div> : <p className="empty-state">لا توجد مهام مسندة.</p>}</section>
  </>
}

function Employees({ employees, team, employee, setEmployee, submit, remove }) {
  const employeeUserIds = new Set(employees.map((item) => item.user))
  const availableTechnicians = team.filter((item) => item.role === 'technician' && !employeeUserIds.has(item.id))
  return <><section className="dashboard-intro"><div><h2>ملفات الموظفين</h2><p>أضف بيانات الفني ونسبة عمولته بعد إنشاء حسابه من شاشة الحسابات.</p></div></section><section className="form-card"><form className="entry-form" onSubmit={(event) => submit(event, '/workforce/employees/', employee, () => setEmployee(emptyEmployee), 'تم إنشاء ملف الموظف.')}><label>حساب الفني<select required value={employee.user} onChange={(e) => setEmployee({ ...employee, user: e.target.value })}><option value="">اختر حساب الفني</option>{availableTechnicians.map((item) => <option key={item.id} value={item.id}>{item.first_name || item.username} {item.last_name}</option>)}</select></label><label>المسمى الوظيفي<input required value={employee.job_title} onChange={(e) => setEmployee({ ...employee, job_title: e.target.value })} /></label><label>تاريخ التوظيف<input required type="date" value={employee.hired_at} onChange={(e) => setEmployee({ ...employee, hired_at: e.target.value })} /></label><label>نسبة العمولة %<input required type="number" min="0" max="100" step="0.01" value={employee.commission_rate} onChange={(e) => setEmployee({ ...employee, commission_rate: e.target.value })} /></label><label className="wide">ملاحظات<textarea value={employee.notes} onChange={(e) => setEmployee({ ...employee, notes: e.target.value })} /></label><button className="primary">إنشاء ملف الموظف</button></form></section><section className="recent-jobs"><div className="section-heading"><h2>الموظفون</h2><span>{employees.length} موظف</span></div>{employees.length ? <div className="record-list">{employees.map((item) => <div className="record-row" key={item.id}><strong>{item.user_name}</strong><span>{item.job_title}</span><span>عمولة {item.commission_rate}%</span><button className="delete-action" type="button" onClick={() => remove('/workforce/employees/', item.id)}>حذف</button></div>)}</div> : <p className="empty-state">أنشئ ملفاً لفني حتى يمكن إسناد المهام إليه.</p>}</section></>
}

function Commissions({ commissions, onGenerate }) {
  const total = commissions.reduce((sum, item) => sum + Number(item.amount), 0)
  return <><section className="dashboard-intro"><div><h2>تقرير العمولات</h2><p>يُحتسب من قيمة الخدمات والقطع للبطاقات المسلّمة، ويُوزّع بالتساوي على الفنيين الذين أكملوا مهاماً فيها.</p></div><button className="primary compact" type="button" onClick={onGenerate}>احتساب الشهر الحالي</button></section><section className="inventory-summary"><article><span>إجمالي العمولات</span><strong>{total.toFixed(2)} ر.س</strong></article><article><span>سجلات الاستحقاق</span><strong>{commissions.length}</strong></article><article><span>الحالة</span><strong>جاهز</strong></article></section><section className="recent-jobs"><div className="section-heading"><h2>التفاصيل</h2></div>{commissions.length ? <div className="record-list">{commissions.map((item) => <div className="record-row" key={item.id}><strong>{item.employee_name || 'فني'}</strong><span>{item.job_number}</span><span>{item.commission_rate}% من {item.basis_amount} ر.س</span><strong>{item.amount} ر.س</strong></div>)}</div> : <p className="empty-state">لا توجد عمولات لهذا الشهر. سلّم بطاقة وأكمل مهامها ثم شغّل الاحتساب.</p>}</section></>
}

function Accounting({ jobs, invoices, expenses, vouchers, profitLoss, expense, setExpense, voucher, setVoucher, submit, update, onCreateInvoice, onGeneratePdf, onRecordPayment, remove }) {
  const [jobCard, setJobCard] = useState('')
  const [payments, setPayments] = useState({})
  const billableJobs = jobs.filter((item) => ['ready', 'delivered'].includes(item.status) && !invoices.some((invoice) => invoice.job_card === item.id))
  return <><section className="dashboard-intro"><div><h2>المحاسبة والتقارير</h2><p>أنشئ الفاتورة من بطاقة العمل الجاهزة، ثم سجّل المصروفات والمدفوعات.</p></div></section>
    <section className="financial-grid"><article><span>الإيرادات قبل الضريبة</span><strong>{Number(profitLoss?.revenue || 0).toFixed(2)} ر.س</strong></article><article><span>تكلفة قطع الغيار</span><strong>{Number(profitLoss?.parts_cost || 0).toFixed(2)} ر.س</strong></article><article><span>المصروفات</span><strong>{Number(profitLoss?.expenses || 0).toFixed(2)} ر.س</strong></article><article className="positive"><span>صافي الربح</span><strong>{Number(profitLoss?.net_profit || 0).toFixed(2)} ر.س</strong></article></section>
    <section className="form-card"><h3>إنشاء فاتورة من بطاقة عمل</h3><form className="entry-form" onSubmit={(event) => { event.preventDefault(); if (jobCard) { onCreateInvoice(jobCard); setJobCard('') } }}><label>بطاقة جاهزة أو مسلّمة<select required value={jobCard} onChange={(e) => setJobCard(e.target.value)}><option value="">اختر البطاقة</option>{billableJobs.map((item) => <option key={item.id} value={item.id}>{item.job_number} — {item.vehicle_label}</option>)}</select></label><button className="primary">إنشاء الفاتورة</button></form></section>
    <section className="recent-jobs"><div className="section-heading"><h2>الفواتير</h2><span>{invoices.length} فاتورة</span></div>{invoices.length ? <div className="record-list">{invoices.map((item) => <div className="invoice-row" key={item.id}><div><strong>{item.invoice_number}</strong><small>{item.customer_name} · {item.vehicle_label}</small></div><span className="job-status">{item.status_label}</span><strong>{item.total} ر.س</strong><div className="invoice-actions">{item.status !== 'paid' && item.status !== 'void' && <><input aria-label="مبلغ الدفعة" type="number" min="0.01" max={Math.max(0, Number(item.total) - Number(item.amount_paid))} step="0.01" placeholder="دفعة" value={payments[item.id] || ''} onChange={(e) => setPayments({ ...payments, [item.id]: e.target.value })} /><button className="text-action" type="button" onClick={() => { if (payments[item.id]) onRecordPayment(item.id, payments[item.id]) }}>تحصيل</button></>}<button className="text-action" type="button" onClick={() => onGeneratePdf(item.id)}>PDF</button></div></div>)}</div> : <p className="empty-state">لا توجد فواتير بعد.</p>}</section>
    <InvoiceManagement invoices={invoices} submit={submit} update={update} remove={remove} />
    <Vouchers vouchers={vouchers} invoices={invoices} voucher={voucher} setVoucher={setVoucher} submit={submit} />
    <section className="form-card"><h3>تسجيل مصروف</h3><form className="entry-form" onSubmit={(event) => submit(event, '/accounting/expenses/', expense, () => setExpense(emptyExpense), 'تم تسجيل المصروف.')}><label>الفئة<select value={expense.category} onChange={(e) => setExpense({ ...expense, category: e.target.value })}><option value="rent">إيجار</option><option value="salary">رواتب</option><option value="utilities">خدمات ومرافق</option><option value="supplies">مستلزمات</option><option value="other">أخرى</option></select></label><label>الوصف<input required value={expense.description} onChange={(e) => setExpense({ ...expense, description: e.target.value })} /></label><label>المبلغ<input required type="number" min="0.01" step="0.01" value={expense.amount} onChange={(e) => setExpense({ ...expense, amount: e.target.value })} /></label><label>التاريخ<input required type="date" value={expense.occurred_at} onChange={(e) => setExpense({ ...expense, occurred_at: e.target.value })} /></label><label>المرجع<input value={expense.reference} onChange={(e) => setExpense({ ...expense, reference: e.target.value })} /></label><button className="primary">تسجيل المصروف</button></form></section>
    <section className="recent-jobs"><div className="section-heading"><h2>آخر المصروفات</h2><span>{expenses.length} سجل</span></div>{expenses.length ? <div className="record-list">{expenses.map((item) => <div className="record-row" key={item.id}><strong>{item.description}</strong><span>{item.category}</span><span>{item.occurred_at}</span><strong>{item.amount} ر.س</strong><button className="delete-action" type="button" onClick={() => remove('/accounting/expenses/', item.id)}>حذف</button></div>)}</div> : <p className="empty-state">لا توجد مصروفات مسجلة.</p>}</section>
  </>
}

function InvoiceManagement({ invoices, submit, update, remove }) {
  return <section className="recent-jobs"><div className="section-heading"><div><h2>تعديل بنود الفاتورة</h2><p>يمكن تصحيح الفاتورة ما دامت مسودة وقبل إصدارها أو تسجيل أي دفعة.</p></div></div>{invoices.length ? <div className="invoice-editor-list">{invoices.map((invoice) => invoice.status === 'draft' ? <InvoiceDraftEditor key={invoice.id} invoice={invoice} submit={submit} update={update} remove={remove} /> : <div className="invoice-editor locked" key={invoice.id}><div><strong>{invoice.invoice_number}</strong><small>الفاتورة {invoice.status_label} ومحفوظة للقراءة فقط.</small></div>{invoice.lines.map((line) => <div className="invoice-line-summary" key={line.id}><span>{line.description}</span><span>{line.quantity} × {line.unit_price} ر.س</span><strong>{line.line_total} ر.س</strong></div>)}</div>)}</div> : <p className="empty-state">لا توجد فواتير بعد.</p>}</section>
}

function InvoiceDraftEditor({ invoice, submit, update, remove }) {
  const [metadata, setMetadata] = useState({ vat_rate: invoice.vat_rate, due_at: invoice.due_at || '', notes: invoice.notes || '' })
  const [lineDrafts, setLineDrafts] = useState(() => Object.fromEntries(invoice.lines.map((line) => [line.id, { description: line.description, quantity: line.quantity, unit_price: line.unit_price, line_type: line.line_type }])))
  const [newLine, setNewLine] = useState({ line_type: 'adjustment', description: '', quantity: '1.00', unit_price: '' })

  useEffect(() => {
    setMetadata({ vat_rate: invoice.vat_rate, due_at: invoice.due_at || '', notes: invoice.notes || '' })
    setLineDrafts(Object.fromEntries(invoice.lines.map((line) => [line.id, { description: line.description, quantity: line.quantity, unit_price: line.unit_price, line_type: line.line_type }])))
  }, [invoice])

  const changeLine = (lineId, field, value) => setLineDrafts({ ...lineDrafts, [lineId]: { ...lineDrafts[lineId], [field]: value } })
  return <div className="invoice-editor"><div className="section-heading"><div><strong>{invoice.invoice_number}</strong><small>{invoice.customer_name} · الإجمالي الحالي {invoice.total} ر.س</small></div><span className="job-status draft">مسودة قابلة للتعديل</span></div>
    <form className="entry-form invoice-metadata" onSubmit={async (event) => { event.preventDefault(); await update(`/accounting/invoices/${invoice.id}/`, { ...metadata, due_at: metadata.due_at || null }, 'تم تحديث بيانات الفاتورة وإعادة احتسابها.') }}><label>نسبة الضريبة %<input required type="number" min="0" step="0.01" value={metadata.vat_rate} onChange={(event) => setMetadata({ ...metadata, vat_rate: event.target.value })} /></label><label>تاريخ الاستحقاق<input type="date" value={metadata.due_at} onChange={(event) => setMetadata({ ...metadata, due_at: event.target.value })} /></label><label>ملاحظات<input value={metadata.notes} onChange={(event) => setMetadata({ ...metadata, notes: event.target.value })} /></label><button className="primary">حفظ بيانات الفاتورة</button></form>
    <div className="invoice-lines-edit">{invoice.lines.map((line) => { const draft = lineDrafts[line.id] || line; return <form className="invoice-line-edit" key={line.id} onSubmit={async (event) => { event.preventDefault(); await update(`/accounting/invoice-lines/${line.id}/`, draft, 'تم تصحيح بند الفاتورة وإعادة احتساب الإجمالي.') }}><label>نوع البند<select value={draft.line_type} onChange={(event) => changeLine(line.id, 'line_type', event.target.value)}><option value="service">خدمة</option><option value="part">قطعة غيار</option><option value="adjustment">تعديل</option></select></label><label>الوصف<input required value={draft.description} onChange={(event) => changeLine(line.id, 'description', event.target.value)} /></label><label>الكمية<input required type="number" min="0.01" step="0.01" value={draft.quantity} onChange={(event) => changeLine(line.id, 'quantity', event.target.value)} /></label><label>سعر الوحدة<input required type="number" min="0" step="0.01" value={draft.unit_price} onChange={(event) => changeLine(line.id, 'unit_price', event.target.value)} /></label><strong>{line.line_total} ر.س</strong><button className="text-action" type="submit">حفظ</button><button className="delete-action" type="button" onClick={() => remove('/accounting/invoice-lines/', line.id)}>حذف</button></form> })}</div>
    <form className="entry-form add-invoice-line" onSubmit={(event) => submit(event, '/accounting/invoice-lines/', { ...newLine, invoice: invoice.id }, () => setNewLine({ line_type: 'adjustment', description: '', quantity: '1.00', unit_price: '' }), 'تمت إضافة بند وإعادة احتساب الفاتورة.')}><label>نوع البند<select value={newLine.line_type} onChange={(event) => setNewLine({ ...newLine, line_type: event.target.value })}><option value="service">خدمة</option><option value="part">قطعة غيار</option><option value="adjustment">تعديل</option></select></label><label>وصف البند<input required value={newLine.description} onChange={(event) => setNewLine({ ...newLine, description: event.target.value })} /></label><label>الكمية<input required type="number" min="0.01" step="0.01" value={newLine.quantity} onChange={(event) => setNewLine({ ...newLine, quantity: event.target.value })} /></label><label>سعر الوحدة<input required type="number" min="0" step="0.01" value={newLine.unit_price} onChange={(event) => setNewLine({ ...newLine, unit_price: event.target.value })} /></label><button className="primary">إضافة بند</button></form>
  </div>
}

function PointOfSale({ invoices, onRecordPayment }) {
  const payableInvoices = invoices.filter((item) => !['paid', 'void', 'draft'].includes(item.status))
  const [invoiceId, setInvoiceId] = useState('')
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('card')
  const [reference, setReference] = useState('')
  const selectedInvoice = payableInvoices.find((item) => item.id === Number(invoiceId))
  const remaining = selectedInvoice ? Math.max(0, Number(selectedInvoice.total) - Number(selectedInvoice.amount_paid)) : 0

  const selectInvoice = (value) => {
    setInvoiceId(value)
    const invoice = payableInvoices.find((item) => item.id === Number(value))
    setAmount(invoice ? Math.max(0, Number(invoice.total) - Number(invoice.amount_paid)).toFixed(2) : '')
  }

  const submitPayment = async (event) => {
    event.preventDefault()
    if (!selectedInvoice || !amount || Number(amount) <= 0 || Number(amount) > remaining) return
    const paid = await onRecordPayment(selectedInvoice.id, amount, method, reference)
    if (paid) {
      setInvoiceId('')
      setAmount('')
      setReference('')
    }
  }

  return <><section className="dashboard-intro"><div><h2>نقطة البيع</h2><p>سجّل سداد الفاتورة فوراً من النقد أو البطاقة أو التحويل، وسيتم تحديث رصيدها وحالتها.</p></div></section>
    <section className="form-card"><form className="entry-form" onSubmit={submitPayment}><label>الفاتورة<select required value={invoiceId} onChange={(event) => selectInvoice(event.target.value)}><option value="">اختر الفاتورة</option>{payableInvoices.map((item) => <option value={item.id} key={item.id}>{item.invoice_number} — {item.customer_name} — المتبقي {Math.max(0, Number(item.total) - Number(item.amount_paid)).toFixed(2)} ر.س</option>)}</select></label><label>وسيلة السداد<select value={method} onChange={(event) => setMethod(event.target.value)}><option value="card">بطاقة مدى/ائتمانية</option><option value="cash">نقدي</option><option value="transfer">تحويل بنكي</option><option value="other">أخرى</option></select></label><label>المبلغ<input required type="number" min="0.01" max={remaining || undefined} step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} /></label><label>مرجع العملية (اختياري)<input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="رقم العملية أو آخر أرقام البطاقة" /></label><button className="primary" disabled={!selectedInvoice || !amount}>تأكيد السداد</button></form></section>
    {selectedInvoice && <section className="financial-grid"><article><span>إجمالي الفاتورة</span><strong>{Number(selectedInvoice.total).toFixed(2)} ر.س</strong></article><article><span>المسدد سابقاً</span><strong>{Number(selectedInvoice.amount_paid).toFixed(2)} ر.س</strong></article><article className="positive"><span>المتبقي للتحصيل</span><strong>{remaining.toFixed(2)} ر.س</strong></article></section>}
    <section className="recent-jobs"><div className="section-heading"><h2>فواتير بانتظار السداد</h2><span>{payableInvoices.length} فاتورة</span></div>{payableInvoices.length ? <div className="record-list">{payableInvoices.map((item) => <div className="invoice-row" key={item.id}><div><strong>{item.invoice_number}</strong><small>{item.customer_name} · {item.vehicle_label}</small></div><span className="job-status">{item.status_label}</span><strong>{Math.max(0, Number(item.total) - Number(item.amount_paid)).toFixed(2)} ر.س</strong><button className="text-action" type="button" onClick={() => selectInvoice(String(item.id))}>تحصيل</button></div>)}</div> : <p className="empty-state">لا توجد فواتير جاهزة للتحصيل.</p>}</section>
  </>
}

function Vouchers({ vouchers, invoices, voucher, setVoucher, submit }) {
  const isReceipt = voucher.voucher_type === 'receipt'
  const payableInvoices = invoices.filter((item) => !['draft', 'void', 'paid'].includes(item.status))
  const chooseInvoice = (invoiceId) => {
    const invoice = payableInvoices.find((item) => item.id === Number(invoiceId))
    setVoucher({ ...voucher, invoice: invoiceId, party_name: invoice?.customer_name || voucher.party_name, amount: invoice ? Math.max(0, Number(invoice.total) - Number(invoice.amount_paid)).toFixed(2) : voucher.amount })
  }
  const switchType = (voucher_type) => setVoucher({ ...emptyVoucher, voucher_type })
  return <><section className="form-card"><h3>سند قبض أو صرف</h3><form className="entry-form" onSubmit={(event) => submit(event, '/accounting/vouchers/', { ...voucher, invoice: isReceipt ? voucher.invoice || null : null }, () => setVoucher(emptyVoucher), 'تم إنشاء السند المحاسبي.')}><label>نوع السند<select value={voucher.voucher_type} onChange={(event) => switchType(event.target.value)}><option value="receipt">سند قبض</option><option value="disbursement">سند صرف</option></select></label>{isReceipt && <label>الفاتورة<select required value={voucher.invoice} onChange={(event) => chooseInvoice(event.target.value)}><option value="">اختر الفاتورة</option>{payableInvoices.map((item) => <option key={item.id} value={item.id}>{item.invoice_number} — {item.customer_name}</option>)}</select></label>}<label>الجهة<input required value={voucher.party_name} onChange={(event) => setVoucher({ ...voucher, party_name: event.target.value })} /></label><label>المبلغ<input required type="number" min="0.01" step="0.01" value={voucher.amount} onChange={(event) => setVoucher({ ...voucher, amount: event.target.value })} /></label><label>التاريخ<input required type="date" value={voucher.occurred_at} onChange={(event) => setVoucher({ ...voucher, occurred_at: event.target.value })} /></label>{isReceipt ? <label>وسيلة القبض<select value={voucher.payment_method} onChange={(event) => setVoucher({ ...voucher, payment_method: event.target.value })}><option value="cash">نقدي</option><option value="card">بطاقة</option><option value="transfer">تحويل</option><option value="other">أخرى</option></select></label> : <label>فئة المصروف<select value={voucher.category} onChange={(event) => setVoucher({ ...voucher, category: event.target.value })}><option value="rent">إيجار</option><option value="salary">رواتب</option><option value="utilities">خدمات ومرافق</option><option value="supplies">مستلزمات</option><option value="other">أخرى</option></select></label>}<label>المرجع<input value={voucher.reference} onChange={(event) => setVoucher({ ...voucher, reference: event.target.value })} /></label><label className="wide">البيان<input required value={voucher.description} onChange={(event) => setVoucher({ ...voucher, description: event.target.value })} /></label><button className="primary">إنشاء السند</button></form></section>
    <section className="recent-jobs"><div className="section-heading"><h2>سندات القبض والصرف</h2><span>{vouchers.length} سند</span></div>{vouchers.length ? <div className="record-list">{vouchers.map((item) => <div className="record-row" key={item.id}><strong>{item.voucher_number}</strong><span>{item.voucher_type_label} · {item.party_name}</span><span>{item.description}</span><strong>{item.amount} ر.س</strong></div>)}</div> : <p className="empty-state">لا توجد سندات محاسبية بعد.</p>}</section>
  </>
}

function Documents({ documents, alerts, customers, vehicles, employees, onUpload, onDownload, onAcknowledge, remove }) {
  const [form, setForm] = useState({ name: '', document_type: '', expires_at: '', ownerType: '', ownerId: '' })
  const [file, setFile] = useState(null)
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
  return <><section className="dashboard-intro"><div><h2>أرشفة الوثائق</h2><p>تُخزن الملفات مشفرة، ولا تُفك إلا أثناء تنزيلها للمستخدم المصرح له.</p></div></section>
    <section className="form-card"><form className="entry-form" onSubmit={upload}><label>اسم الوثيقة<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label>نوع الوثيقة<input required placeholder="رخصة، عقد، شهادة..." value={form.document_type} onChange={(e) => setForm({ ...form, document_type: e.target.value })} /></label><label>تاريخ الانتهاء<input type="date" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} /></label><label>ربط بـ<select value={form.ownerType} onChange={(e) => setForm({ ...form, ownerType: e.target.value, ownerId: '' })}><option value="">الورشة فقط</option><option value="customer">عميل</option><option value="vehicle">مركبة</option><option value="employee">موظف</option></select></label>{form.ownerType && <label>الجهة<select required value={form.ownerId} onChange={(e) => setForm({ ...form, ownerId: e.target.value })}><option value="">اختر</option>{ownerOptions.map((item) => <option key={item.id} value={item.id}>{optionLabel(item)}</option>)}</select></label>}<label>الملف<input required type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label><button className="primary">رفع وتشفير الوثيقة</button></form></section>
    <section className="recent-jobs"><div className="section-heading"><h2>تنبيهات انتهاء الصلاحية</h2><span>{alerts.filter((item) => !item.acknowledged_at).length} جديد</span></div>{alerts.length ? <div className="record-list">{alerts.map((item) => <div className={`record-row ${item.acknowledged_at ? '' : 'low-stock-row'}`} key={item.id}><strong>{item.document_name}</strong><span>ينتهي: {item.expires_at}</span><span>خلال {item.days_before} يوم</span>{item.acknowledged_at ? <span>تمت القراءة</span> : <button className="text-action" type="button" onClick={() => onAcknowledge(item.id)}>تأكيد</button>}</div>)}</div> : <p className="empty-state">لا توجد تنبيهات صلاحية حالياً.</p>}</section>
    <section className="recent-jobs"><div className="section-heading"><h2>الوثائق المؤرشفة</h2><span>{documents.length} وثيقة</span></div>{documents.length ? <div className="record-list">{documents.map((item) => <div className="document-row" key={item.id}><div><strong>{item.name}</strong><small>{item.document_type} · {item.owner_label}</small></div><span>{item.expires_at || 'بلا انتهاء'}</span><span>{item.original_filename}</span><div><button className="text-action" type="button" onClick={() => onDownload(item)}>تنزيل</button><button className="delete-action" type="button" onClick={() => remove('/documents/documents/', item.id)}>حذف</button></div></div>)}</div> : <p className="empty-state">لا توجد وثائق مؤرشفة بعد.</p>}</section>
  </>
}

function Inventory({ suppliers, parts, lowStock, alerts, partUsages, partRequests, jobs, supplier, setSupplier, part, setPart, partUsage, setPartUsage, partRequest, setPartRequest, submit, update, remove, onAcknowledge, onReviewRequest, canManage, canIssue, isTechnician }) {
  const saveSupplier = async (event) => {
    if (!supplier.id) return submit(event, '/inventory/suppliers/', supplier, () => setSupplier(emptySupplier), 'تمت إضافة المورد.')
    event.preventDefault()
    if (await update(`/inventory/suppliers/${supplier.id}/`, supplier, 'تم تحديث بيانات المورد.')) setSupplier(emptySupplier)
  }
  const activeJobs = jobs.filter((item) => ['pending', 'in_progress'].includes(item.status))
  return <><section className="dashboard-intro"><div><h2>{isTechnician ? 'طلبات قطع الغيار' : 'المخزون وقطع الغيار'}</h2><p>{isTechnician ? 'اطلب القطعة مباشرة للبطاقة المسندة إليك وتابع حالة الصرف.' : 'تُراجع الطلبات ثم تخصم الكمية تلقائياً عند الصرف.'}</p></div></section>
    <section className="inventory-summary"><article><span>قطع نشطة</span><strong>{parts.filter((item) => item.is_active).length}</strong></article><article className="warning"><span>تحت حد الطلب</span><strong>{lowStock.length}</strong></article><article><span>طلبات معلقة</span><strong>{partRequests.filter((item) => ['requested', 'approved'].includes(item.status)).length}</strong></article></section>
    {isTechnician && <section className="form-card"><h3>طلب قطعة غيار</h3><form className="entry-form" onSubmit={(event) => submit(event, '/inventory/part-requests/', partRequest, () => setPartRequest(emptyPartRequest), 'تم إرسال طلب القطعة للمخزن.')}><label>بطاقة العمل<select required value={partRequest.job_card} onChange={(e) => setPartRequest({ ...partRequest, job_card: e.target.value })}><option value="">اختر البطاقة</option>{activeJobs.map((item) => <option key={item.id} value={item.id}>{item.job_number} — {item.vehicle_label}</option>)}</select></label><label>قطعة الغيار<select required value={partRequest.part} onChange={(e) => setPartRequest({ ...partRequest, part: e.target.value })}><option value="">اختر القطعة</option>{parts.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.sku} — {item.name} ({item.quantity} متاح)</option>)}</select></label><label>الكمية<input required type="number" min="1" value={partRequest.quantity} onChange={(e) => setPartRequest({ ...partRequest, quantity: e.target.value })} /></label><label className="wide">ملاحظات<textarea value={partRequest.notes} onChange={(e) => setPartRequest({ ...partRequest, notes: e.target.value })} /></label><button className="primary">إرسال الطلب</button></form></section>}
    {canManage && <><section className="form-card"><h3>{supplier.id ? 'تحديث المورد' : 'إضافة مورد'}</h3><form className="entry-form" onSubmit={saveSupplier}><label>اسم المورد<input required value={supplier.name} onChange={(e) => setSupplier({ ...supplier, name: e.target.value })} /></label><label>جهة الاتصال<input value={supplier.contact_name} onChange={(e) => setSupplier({ ...supplier, contact_name: e.target.value })} /></label><label>الهاتف<input value={supplier.phone} onChange={(e) => setSupplier({ ...supplier, phone: e.target.value })} /></label><label>البريد<input type="email" value={supplier.email} onChange={(e) => setSupplier({ ...supplier, email: e.target.value })} /></label><label className="wide">ملاحظات<textarea value={supplier.notes} onChange={(e) => setSupplier({ ...supplier, notes: e.target.value })} /></label><button className="primary">{supplier.id ? 'حفظ التحديث' : 'إضافة المورد'}</button>{supplier.id && <button type="button" className="subtle" onClick={() => setSupplier(emptySupplier)}>إلغاء</button>}</form></section><section className="recent-jobs"><div className="section-heading"><h2>الموردون</h2><span>{suppliers.length} مورد</span></div>{suppliers.length ? <div className="record-list">{suppliers.map((item) => <div className="record-row" key={item.id}><strong>{item.name}</strong><span>{item.contact_name || '—'} · {item.phone || '—'}</span><span>{item.email || '—'}</span><button className="text-action" type="button" onClick={() => setSupplier(item)}>تعديل</button><button className="delete-action" type="button" onClick={() => remove('/inventory/suppliers/', item.id)}>حذف</button></div>)}</div> : <p className="empty-state">لا يوجد موردون بعد.</p>}</section>
    <section className="form-card"><h3>إضافة قطعة غيار</h3><form className="entry-form" onSubmit={(event) => submit(event, '/inventory/parts/', { ...part, supplier: part.supplier || null }, () => setPart(emptyPart), 'تمت إضافة قطعة الغيار.')}><label>اسم القطعة<input required value={part.name} onChange={(e) => setPart({ ...part, name: e.target.value })} /></label><label>رمز القطعة<input required value={part.sku} onChange={(e) => setPart({ ...part, sku: e.target.value })} /></label><label>المورد<select value={part.supplier} onChange={(e) => setPart({ ...part, supplier: e.target.value })}><option value="">بدون مورد</option>{suppliers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>الكمية الحالية<input required type="number" min="0" value={part.quantity} onChange={(e) => setPart({ ...part, quantity: e.target.value })} /></label><label>حد إعادة الطلب<input required type="number" min="0" value={part.reorder_level} onChange={(e) => setPart({ ...part, reorder_level: e.target.value })} /></label><label>سعر الشراء<input required type="number" min="0" step="0.01" value={part.purchase_price} onChange={(e) => setPart({ ...part, purchase_price: e.target.value })} /></label><label>سعر البيع<input required type="number" min="0" step="0.01" value={part.sale_price} onChange={(e) => setPart({ ...part, sale_price: e.target.value })} /></label><button className="primary">إضافة القطعة</button></form></section></>}
    {canIssue && <section className="form-card"><h3>صرف مباشر</h3><form className="entry-form" onSubmit={(event) => submit(event, '/inventory/part-usages/', partUsage, () => setPartUsage(emptyPartUsage), 'تم صرف القطعة وتحديث المخزون.')}><label>بطاقة العمل<select required value={partUsage.job_card} onChange={(e) => setPartUsage({ ...partUsage, job_card: e.target.value })}><option value="">اختر البطاقة</option>{activeJobs.map((item) => <option key={item.id} value={item.id}>{item.job_number} — {item.vehicle_label}</option>)}</select></label><label>قطعة الغيار<select required value={partUsage.part} onChange={(e) => setPartUsage({ ...partUsage, part: e.target.value })}><option value="">اختر القطعة</option>{parts.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.sku} — {item.name} ({item.quantity})</option>)}</select></label><label>الكمية<input required type="number" min="1" value={partUsage.quantity} onChange={(e) => setPartUsage({ ...partUsage, quantity: e.target.value })} /></label><button className="primary">صرف القطعة</button></form></section>}
    <section className="recent-jobs"><div className="section-heading"><h2>طلبات القطع</h2><span>{partRequests.length} طلب</span></div>{partRequests.length ? <div className="record-list">{partRequests.map((item) => <div className="record-row" key={item.id}><strong>{item.job_number} — {item.part_name}</strong><span>{item.requested_by_name} · {item.quantity} قطعة</span><span className="job-status">{item.status_label}</span>{canIssue && ['requested', 'approved'].includes(item.status) && <><button className="text-action" type="button" onClick={() => onReviewRequest(item.id, 'fulfill')}>صرف</button><button className="delete-action" type="button" onClick={() => onReviewRequest(item.id, 'reject')}>رفض</button></>}</div>)}</div> : <p className="empty-state">لا توجد طلبات قطع.</p>}</section>
    <section className="recent-jobs"><div className="section-heading"><h2>قطع الغيار</h2><span>{parts.length} قطعة</span></div>{parts.length ? <div className="record-list">{parts.map((item) => <div className={`record-row ${item.is_low_stock ? 'low-stock-row' : ''}`} key={item.id}><strong>{item.sku} — {item.name}</strong><span>{item.quantity} متاح / حد الطلب {item.reorder_level}</span><span>{item.supplier_name || 'بدون مورد'} · {item.sale_price} ر.س</span>{canManage && <button className="delete-action" type="button" onClick={() => remove('/inventory/parts/', item.id)}>حذف</button>}</div>)}</div> : <p className="empty-state">لا توجد قطع غيار.</p>}</section>
    {canManage && <section className="recent-jobs"><div className="section-heading"><h2>تنبيهات الحد الأدنى</h2><span>{alerts.filter((item) => item.is_active).length} فعّال</span></div>{alerts.filter((item) => item.is_active).map((item) => <div className="record-row low-stock-row" key={item.id}><strong>{item.part_sku} — {item.part_name}</strong><span>المتاح: {item.quantity_at_alert}</span><button className="text-action" type="button" onClick={() => onAcknowledge(item.id)}>تأكيد الاطلاع</button></div>)}</section>}
    {!isTechnician && <section className="recent-jobs"><div className="section-heading"><h2>آخر حركات الصرف</h2><span>{partUsages.length} حركة</span></div>{partUsages.map((item) => <div className="record-row" key={item.id}><strong>{item.job_number} — {item.part_sku}</strong><span>{item.part_name}</span><span>{item.quantity} × {item.unit_sale_price} ر.س</span></div>)}</section>}
  </>
}

function Records({ title, form, items, columns, onDelete }) {
  return <><section className="dashboard-intro"><div><h2>{title}</h2><p>أضف البيانات لتصبح متاحة عند فتح بطاقات العمل.</p></div></section><section className="form-card">{form}</section><section className="recent-jobs"><div className="section-heading"><h2>السجلات</h2><span>{items.length} سجل</span></div>{items.length ? <div className="record-list">{items.map((item) => <div className="record-row" key={item.id}>{columns(item)}{onDelete && <button className="delete-action" type="button" onClick={() => onDelete(item.id)}>حذف</button>}</div>)}</div> : <p className="empty-state">لا توجد سجلات بعد.</p>}</section></>
}

export default Workspace
