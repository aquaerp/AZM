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
    jobs: [...(options.jobs || [])],
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
    if (method === 'POST' && path === '/auth/refresh/') return json(route, { access: 'renewed-access-token', refresh: 'renewed-refresh-token' })
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
    if (method === 'GET' && path === '/accounting/invoices/') return json(route, state.invoices)
    if (method === 'GET' && path === '/accounting/reports/profit-loss/') return json(route, { revenue: '0.00', parts_cost: '0.00', expenses: '0.00', net_profit: '0.00' })

    if (method === 'POST' && path === '/workshop/customers/') {
      if (state.customerError) return json(route, state.customerError, 400)
      const customer = { id: state.customers.length + 1, ...payload }
      state.customers.push(customer)
      return json(route, customer, 201)
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
