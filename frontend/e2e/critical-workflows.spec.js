import { expect, test } from '@playwright/test'
import { installMockApi, login } from './mock-api.js'

test('يسجل المالك الدخول ويضيف عميلاً دون إعادة تسجيل الدخول', async ({ page }) => {
  const state = await installMockApi(page)
  await login(page)

  await page.getByRole('button', { name: 'العملاء' }).click()
  await page.getByLabel('الاسم').fill('عميل تجريبي')
  await page.getByLabel('الهاتف').fill('0500000000')
  await page.getByLabel('البريد').fill('customer@example.com')
  await page.getByRole('button', { name: 'إضافة العميل' }).click()

  await expect(page.getByRole('status')).toContainText('تمت إضافة العميل')
  await expect(page.getByText('عميل تجريبي')).toBeVisible()
  expect(state.requests.some(({ method, path, payload }) => method === 'POST' && path === '/workshop/customers/' && payload.phone === '0500000000')).toBeTruthy()
})

test('يصحح المحاسب قيمة بند في فاتورة مسودة', async ({ page }) => {
  const state = await installMockApi(page, {
    role: 'accountant',
    invoices: [{
      id: 7,
      invoice_number: 'INV-000007',
      job_card: 3,
      customer_name: 'عميل الفاتورة',
      vehicle_label: 'ABC 1234',
      status: 'draft',
      status_label: 'مسودة',
      vat_rate: '0.00',
      due_at: null,
      notes: '',
      subtotal: '100.00',
      total: '100.00',
      amount_paid: '0.00',
      lines: [{ id: 11, line_type: 'service', description: 'صيانة', quantity: '1.00', unit_price: '100.00', line_total: '100.00' }],
    }],
  })
  await login(page)

  await page.getByRole('button', { name: 'المحاسبة' }).click()
  const line = page.locator('.invoice-line-edit')
  await line.getByLabel('سعر الوحدة').fill('175.50')
  await line.getByRole('button', { name: 'حفظ', exact: true }).click()

  await expect(page.getByRole('status')).toContainText('تم تصحيح بند الفاتورة')
  expect(state.requests.some(({ method, path, payload }) => method === 'PATCH' && path === '/accounting/invoice-lines/11/' && payload.unit_price === '175.50')).toBeTruthy()
})

test('تسلم الورشة البطاقة الجاهزة وتغلقها للعميل', async ({ page }) => {
  const state = await installMockApi(page, {
    jobs: [{
      id: 9,
      job_number: 'JOB-000009',
      vehicle_label: 'XYZ 9876',
      customer_name: 'عميل التسليم',
      complaint: 'صيانة دورية',
      promised_at: '2026-08-22T10:00:00Z',
      status: 'ready',
      status_label: 'جاهزة للاستلام',
    }],
  })
  page.on('dialog', (dialog) => dialog.accept())
  await login(page)

  await page.getByRole('button', { name: 'تسليم للعميل' }).click()

  await expect(page.getByRole('status')).toContainText('تم تسليم المركبة')
  await expect(page.locator('.job-status.delivered')).toHaveText('تم التسليم')
  expect(state.requests.some(({ method, path }) => method === 'POST' && path === '/workshop/job-cards/9/deliver/')).toBeTruthy()
})

test('لا تظهر الوظائف المالية أو الإدارية للفني', async ({ page }) => {
  await installMockApi(page, { role: 'technician' })
  await login(page)

  await expect(page.getByRole('button', { name: 'طلبات قطع الغيار' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'المحاسبة' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'العملاء' })).toHaveCount(0)
})

test('يجدد الرمز المنتهي ويواصل العمل دون إخراج المستخدم', async ({ page }) => {
  const state = await installMockApi(page, { expireDashboardOnce: true })
  await login(page)

  await expect(page.locator('.workspace')).toBeVisible()
  await expect(page.getByRole('button', { name: 'تسجيل الخروج' })).toBeVisible()
  expect(state.requests.some(({ method, path }) => method === 'POST' && path === '/auth/refresh/')).toBeTruthy()
  expect(state.dashboardAttempts).toBeGreaterThanOrEqual(2)
})

test('يعرض خطأ الإدخال المفهوم ويبقي المستخدم داخل جلسته', async ({ page }) => {
  await installMockApi(page, { customerError: { phone: ['رقم الهاتف مستخدم لعميل آخر.'] } })
  await login(page)

  await page.getByRole('button', { name: 'العملاء' }).click()
  await page.getByLabel('الاسم').fill('عميل مكرر')
  await page.getByLabel('الهاتف').fill('0500000000')
  await page.getByRole('button', { name: 'إضافة العميل' }).click()

  await expect(page.getByRole('alert')).toContainText('رقم الهاتف مستخدم لعميل آخر')
  await expect(page.getByRole('button', { name: 'تسجيل الخروج' })).toBeVisible()
})

test('يضيف المالك مركبة ويربطها بالعميل دون إعادة تسجيل الدخول', async ({ page }) => {
  const state = await installMockApi(page, {
    customers: [{ id: 5, name: 'مالك المركبة', phone: '0500000001', email: '' }],
  })
  await login(page)

  await page.getByRole('button', { name: 'المركبات' }).click()
  await page.getByLabel('العميل').selectOption('5')
  await page.getByLabel('رقم اللوحة').fill('AZM 2026')
  await page.getByLabel('الشركة').fill('تويوتا')
  await page.getByLabel('الموديل').fill('كامري')
  await page.getByLabel('سنة الصنع').fill('2024')
  await page.getByRole('button', { name: 'إضافة المركبة' }).click()

  await expect(page.getByRole('status')).toContainText('تمت إضافة المركبة')
  await expect(page.getByText('AZM 2026')).toBeVisible()
  expect(state.requests.some(({ method, path, payload }) => method === 'POST' && path === '/workshop/vehicles/' && payload.customer === '5')).toBeTruthy()
})

test('يفتح المالك بطاقة عمل مرتبطة بالمركبة والخدمة والفني', async ({ page }) => {
  const state = await installMockApi(page, {
    customers: [{ id: 5, name: 'عميل البطاقة', phone: '0500000002' }],
    vehicles: [{ id: 8, customer: 5, customer_name: 'عميل البطاقة', license_plate: 'JOB 2026', make: 'هيونداي', model: 'اكسنت' }],
    services: [{ id: 13, name: 'فحص شامل', base_price: '250.00', is_active: true }],
    team: [{ id: 21, username: 'tech', first_name: 'الفني', last_name: 'الأول', role: 'technician' }],
  })
  await login(page)

  await page.getByRole('button', { name: 'بطاقات العمل' }).click()
  await page.getByLabel('العميل').selectOption('5')
  await page.getByLabel('المركبة').selectOption('8')
  await page.getByLabel('الخدمات').selectOption('13')
  await page.getByLabel('الفنيون').selectOption('21')
  await page.getByLabel('وصف العطل').fill('صوت غير طبيعي في المحرك')
  await page.getByLabel('التكلفة التقديرية').fill('250')
  await page.getByRole('button', { name: 'فتح بطاقة عمل' }).click()

  await expect(page.getByRole('status')).toContainText('تم فتح بطاقة العمل')
  await expect(page.getByText('صوت غير طبيعي في المحرك')).toBeVisible()
  expect(state.requests.some(({ method, path, payload }) => method === 'POST' && path === '/workshop/job-cards/' && payload.vehicle === '8' && payload.service_ids[0] === 13 && payload.technician_ids[0] === 21)).toBeTruthy()
})

test('يرسل الفني طلب قطعة للبطاقة المسندة من داخل النظام', async ({ page }) => {
  const state = await installMockApi(page, {
    role: 'technician',
    jobs: [{ id: 9, job_number: 'JOB-000009', vehicle_label: 'REQ 2026', customer_name: 'عميل', complaint: 'إصلاح', status: 'in_progress', status_label: 'قيد الإصلاح' }],
    parts: [{ id: 4, name: 'فلتر زيت', sku: 'FLT-01', quantity: 8, sale_price: '45.00', is_active: true, is_low_stock: false }],
  })
  await login(page)

  await page.getByRole('button', { name: 'طلبات قطع الغيار' }).click()
  const requestForm = page.locator('.form-card').filter({ hasText: 'طلب قطعة غيار' })
  await requestForm.getByLabel('بطاقة العمل').selectOption('9')
  await requestForm.getByLabel('قطعة الغيار').selectOption('4')
  await requestForm.getByLabel('الكمية').fill('2')
  await requestForm.getByLabel('ملاحظات').fill('مطلوبة لإكمال الإصلاح')
  await requestForm.getByRole('button', { name: 'إرسال الطلب' }).click()

  await expect(page.getByRole('status')).toContainText('تم إرسال طلب القطعة للمخزن')
  await expect(page.getByText('JOB-000009 — فلتر زيت')).toBeVisible()
  expect(state.requests.some(({ method, path, payload }) => method === 'POST' && path === '/inventory/part-requests/' && payload.quantity === '2')).toBeTruthy()
})

test('يصرف أمين المخزن الطلب ويحدث كمية القطعة', async ({ page }) => {
  const state = await installMockApi(page, {
    role: 'storekeeper',
    parts: [{ id: 4, name: 'فلتر زيت', sku: 'FLT-01', quantity: 8, reorder_level: 2, sale_price: '45.00', supplier_name: 'المورد', is_active: true, is_low_stock: false }],
    partRequests: [{ id: 3, job_card: 9, part: 4, job_number: 'JOB-000009', part_name: 'فلتر زيت', requested_by_name: 'الفني', quantity: 2, status: 'requested', status_label: 'مطلوب' }],
  })
  await login(page)

  await page.getByRole('button', { name: 'المخزون' }).click()
  await page.getByRole('button', { name: 'صرف', exact: true }).click()

  await expect(page.getByRole('status')).toContainText('تم صرف القطعة وتحديث المخزون')
  await expect(page.getByText('6 متاح / حد الطلب 2')).toBeVisible()
  expect(state.requests.some(({ method, path }) => method === 'POST' && path === '/inventory/part-requests/3/fulfill/')).toBeTruthy()
})

test('يسجل المحاسب سداد الفاتورة بالكامل من نقطة البيع', async ({ page }) => {
  const state = await installMockApi(page, {
    role: 'accountant',
    invoices: [{
      id: 12,
      invoice_number: 'INV-000012',
      job_card: 9,
      customer_name: 'عميل السداد',
      vehicle_label: 'PAY 2026',
      status: 'issued',
      status_label: 'صادرة',
      total: '300.00',
      amount_paid: '100.00',
      lines: [],
    }],
  })
  await login(page)

  await page.getByRole('button', { name: 'نقطة البيع' }).click()
  await page.getByLabel('الفاتورة').selectOption('12')
  await page.getByLabel('وسيلة السداد').selectOption('card')
  await page.getByLabel('مرجع العملية (اختياري)').fill('POS-7788')
  await page.getByRole('button', { name: 'تأكيد السداد' }).click()

  await expect(page.getByRole('status')).toContainText('تم تسجيل الدفعة وتحديث حالة الفاتورة')
  await expect(page.getByText('لا توجد فواتير جاهزة للتحصيل')).toBeVisible()
  expect(state.requests.some(({ method, path, payload }) => method === 'POST' && path === '/accounting/invoices/12/record-payment/' && payload.amount === '200.00' && payload.reference === 'POS-7788')).toBeTruthy()
})

test('يحتسب المحاسب عمولات الشهر ويعرض تفاصيل الاستحقاق', async ({ page }) => {
  const state = await installMockApi(page, {
    role: 'accountant',
    generatedCommissions: [{ id: 1, employee_name: 'فني العمولة', job_number: 'JOB-000020', commission_rate: '10.00', basis_amount: '500.00', amount: '50.00' }],
  })
  await login(page)

  await page.getByRole('button', { name: 'العمولات' }).click()
  await page.getByRole('button', { name: 'احتساب الشهر الحالي' }).click()

  await expect(page.getByRole('status')).toContainText('تم احتساب عمولات الشهر الحالي')
  await expect(page.getByText('فني العمولة')).toBeVisible()
  await expect(page.locator('.inventory-summary article').first()).toContainText('50.00 ر.س')
  expect(state.requests.some(({ method, path, payload }) => method === 'POST' && path === '/workforce/commissions/generate/' && payload.year && payload.month)).toBeTruthy()
})
