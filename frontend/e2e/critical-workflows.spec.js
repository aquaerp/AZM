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
