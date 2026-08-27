const json = (route, body, status = 200) => route.fulfill({
  status,
  contentType: 'application/json',
  body: JSON.stringify(body),
})

const emptyDashboard = { counts: { pending: 0, in_progress: 0, ready: 0, delivered: 0, cancelled: 0 } }

export async function installMockApi(page, options = {}) {
  const state = {
    role: options.role || 'owner',
    customers: [...(options.customers || [])],
    vehicles: [...(options.vehicles || [])],
    services: [...(options.services || [])],
    team: [...(options.team || [])],
    jobs: [...(options.jobs || [])],
    tasks: [...(options.tasks || [])],
    suppliers: [...(options.suppliers || [])],
    parts: [...(options.parts || [])],
    partUsages: [...(options.partUsages || [])],
    partRequests: [...(options.partRequests || [])],
    commissions: [...(options.commissions || [])],
    generatedCommissions: [...(options.generatedCommissions || [])],
    invoices: [...(options.invoices || [])],
    requests: [],
    expireDashboardOnce: Boolean(options.expireDashboardOnce),
    dashboardAttempts: 0,
    customerError: options.customerError || null,
  }

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const method = request.method()
    const path = new URL(request.url()).pathname.replace(/^\/api/, '')
    const payload = request.postDataJSON?.() || null
    state.requests.push({ method, path, payload })

    if (method === 'POST' && path === '/auth/login/') return json(route, { access: 'access-token', refresh: 'refresh-token' })
    if (method === 'POST' && path === '/auth/token/refresh/') return json(route, { access: 'renewed-access-token', refresh: 'renewed-refresh-token' })
    if (method === 'GET' && path === '/auth/me/') return json(route, {
      id: 1,
      username: state.role,
      first_name: 'مستخدم الاختبار',
      role: state.role,
      is_superuser: false,
      workshop: { id: 1, name: 'ورشة الاختبار' },
    })
    if (method === 'GET' && path === '/auth/workshop/') return json(route, { id: 1, name: 'ورشة الاختبار' })
    if (method === 'GET' && path === '/workshop/job-cards/dashboard/') {
      state.dashboardAttempts += 1
      if (state.expireDashboardOnce && state.dashboardAttempts === 1) return json(route, { detail: 'Token expired' }, 401)
      return json(route, emptyDashboard)
    }
    if (method === 'GET' && path === '/workshop/job-cards/') return json(route, state.jobs)
    if (method === 'GET' && path === '/workshop/customers/') return json(route, state.customers)
    if (method === 'GET' && path === '/workshop/vehicles/') return json(route, state.vehicles)
    if (method === 'GET' && path === '/workshop/services/') return json(route, state.services)
    if (method === 'GET' && path === '/auth/team/') return json(route, state.team)
    if (method === 'GET' && path === '/workforce/tasks/') return json(route, state.tasks)
    if (method === 'GET' && path === '/workforce/commissions/') return json(route, state.commissions)
    if (method === 'GET' && path === '/inventory/suppliers/') return json(route, state.suppliers)
    if (method === 'GET' && path === '/inventory/parts/') return json(route, state.parts)
    if (method === 'GET' && path === '/inventory/parts/low-stock/') return json(route, state.parts.filter((part) => part.is_low_stock))
    if (method === 'GET' && path === '/inventory/part-usages/') return json(route, state.partUsages)
    if (method === 'GET' && path === '/inventory/part-requests/') return json(route, state.partRequests)
    if (method === 'GET' && path === '/accounting/invoices/') return json(route, state.invoices)
    if (method === 'GET' && path === '/accounting/reports/profit-loss/') return json(route, { revenue: '0.00', parts_cost: '0.00', expenses: '0.00', net_profit: '0.00' })

    if (method === 'POST' && path === '/workshop/customers/') {
      if (state.customerError) return json(route, state.customerError, 400)
      const customer = { id: state.customers.length + 1, ...payload }
      state.customers.push(customer)
      return json(route, customer, 201)
    }
    if (method === 'POST' && path === '/workshop/vehicles/') {
      const customer = state.customers.find((item) => item.id === Number(payload.customer))
      const vehicle = { id: state.vehicles.length + 1, ...payload, customer: Number(payload.customer), customer_name: customer?.name || '' }
      state.vehicles.push(vehicle)
      return json(route, vehicle, 201)
    }
    if (method === 'POST' && path === '/workshop/job-cards/') {
      const customer = state.customers.find((item) => item.id === Number(payload.customer))
      const vehicle = state.vehicles.find((item) => item.id === Number(payload.vehicle))
      const job = {
        id: state.jobs.length + 1,
        job_number: `JOB-${String(state.jobs.length + 1).padStart(6, '0')}`,
        ...payload,
        customer: Number(payload.customer),
        vehicle: Number(payload.vehicle),
        customer_name: customer?.name || '',
        vehicle_label: vehicle ? `${vehicle.license_plate} — ${vehicle.make} ${vehicle.model}` : '',
        status: 'pending',
        status_label: 'بانتظار الفحص',
      }
      state.jobs.push(job)
      return json(route, job, 201)
    }
    if (method === 'POST' && path === '/inventory/part-requests/') {
      const job = state.jobs.find((item) => item.id === Number(payload.job_card))
      const part = state.parts.find((item) => item.id === Number(payload.part))
      const requestRecord = {
        id: state.partRequests.length + 1,
        ...payload,
        job_card: Number(payload.job_card),
        part: Number(payload.part),
        job_number: job?.job_number || '',
        part_name: part?.name || '',
        requested_by_name: 'مستخدم الاختبار',
        status: 'requested',
        status_label: 'مطلوب',
      }
      state.partRequests.push(requestRecord)
      return json(route, requestRecord, 201)
    }
    if (method === 'POST' && path === '/inventory/part-usages/') {
      const part = state.parts.find((item) => item.id === Number(payload.part))
      const job = state.jobs.find((item) => item.id === Number(payload.job_card))
      if (part) part.quantity -= Number(payload.quantity)
      const usage = {
        id: state.partUsages.length + 1,
        ...payload,
        job_card: Number(payload.job_card),
        part: Number(payload.part),
        job_number: job?.job_number || '',
        part_name: part?.name || '',
        part_sku: part?.sku || '',
        unit_sale_price: part?.sale_price || '0.00',
      }
      state.partUsages.push(usage)
      return json(route, usage, 201)
    }
    if (method === 'POST' && /^\/inventory\/part-requests\/\d+\/fulfill\/$/.test(path)) {
      const requestId = Number(path.match(/\d+/)[0])
      const requestRecord = state.partRequests.find((item) => item.id === requestId)
      const part = state.parts.find((item) => item.id === Number(requestRecord?.part))
      if (requestRecord) {
        requestRecord.status = 'fulfilled'
        requestRecord.status_label = 'تم الصرف'
      }
      if (part && requestRecord) part.quantity -= Number(requestRecord.quantity)
      return json(route, requestRecord)
    }
    if (method === 'POST' && path === '/workforce/commissions/generate/') {
      state.commissions = [...state.generatedCommissions]
      return json(route, state.commissions)
    }
    if (method === 'POST' && /^\/accounting\/invoices\/\d+\/record-payment\/$/.test(path)) {
      const invoiceId = Number(path.match(/\d+/)[0])
      const invoice = state.invoices.find((item) => item.id === invoiceId)
      if (invoice) {
        const paid = Number(invoice.amount_paid) + Number(payload.amount)
        invoice.amount_paid = paid.toFixed(2)
        invoice.status = paid >= Number(invoice.total) ? 'paid' : 'issued'
        invoice.status_label = invoice.status === 'paid' ? 'مدفوعة' : 'صادرة'
      }
      return json(route, { id: 1, invoice: invoiceId, ...payload }, 201)
    }
    if (method === 'POST' && /^\/accounting\/invoices\/\d+\/generate_pdf\/$/.test(path)) {
      const invoiceId = Number(path.match(/\d+/)[0])
      const invoice = state.invoices.find((item) => item.id === invoiceId)
      return json(route, { ...invoice, pdf_url: `/media/invoices/${invoice?.invoice_number}.pdf` })
    }
    if (method === 'GET' && /^\/accounting\/invoices\/\d+\/download-pdf\/$/.test(path)) {
      return route.fulfill({ status: 200, contentType: 'application/pdf', body: '%PDF-1.4 UAT' })
    }
    if (method === 'PATCH' && /^\/accounting\/invoice-lines\/\d+\/$/.test(path)) {
      const lineId = Number(path.match(/\d+/)[0])
      let updatedLine
      state.invoices = state.invoices.map((invoice) => {
        const lines = invoice.lines.map((line) => {
          if (line.id !== lineId) return line
          updatedLine = { ...line, ...payload }
          updatedLine.line_total = (Number(updatedLine.quantity) * Number(updatedLine.unit_price)).toFixed(2)
          return updatedLine
        })
        const subtotal = lines.reduce((sum, line) => sum + Number(line.line_total), 0)
        return { ...invoice, lines, subtotal: subtotal.toFixed(2), total: subtotal.toFixed(2) }
      })
      return json(route, updatedLine)
    }
    if (method === 'POST' && /^\/workshop\/job-cards\/\d+\/deliver\/$/.test(path)) {
      const jobId = Number(path.match(/\d+/)[0])
      state.jobs = state.jobs.map((job) => job.id === jobId ? { ...job, status: 'delivered', status_label: 'تم التسليم' } : job)
      return json(route, state.jobs.find((job) => job.id === jobId))
    }

    if (method === 'GET') return json(route, [])
    return json(route, payload || {}, method === 'POST' ? 201 : 200)
  })

  return state
}

export async function login(page) {
  await page.goto('/')
  await page.getByLabel('اسم المستخدم').fill('owner')
  await page.getByLabel('كلمة المرور').fill('password')
  await page.getByRole('button', { name: 'دخول', exact: true }).click()
  await page.locator('.workspace').waitFor()
}
