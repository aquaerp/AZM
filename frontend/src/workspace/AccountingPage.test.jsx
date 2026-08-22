import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { emptyExpense, emptyVoucher } from './AccountingDefaults.js'
import AccountingPage from './AccountingPage.jsx'

const jobs = [
  { id: 1, job_number: 'JOB-1', vehicle_label: 'مركبة 1', status: 'ready' },
  { id: 2, job_number: 'JOB-2', vehicle_label: 'مركبة 2', status: 'delivered' },
]

const invoices = [
  { id: 1, job_card: 1, invoice_number: 'INV-1', customer_name: 'عميل 1', vehicle_label: 'مركبة 1', status: 'issued', status_label: 'صادرة', total: '100.00', amount_paid: '10.00', vat_rate: '15.00', due_at: null, notes: '', lines: [{ id: 11, description: 'خدمة', quantity: '1.00', unit_price: '100.00', line_total: '100.00', line_type: 'service' }] },
  { id: 2, job_card: 3, invoice_number: 'INV-2', customer_name: 'عميل 2', vehicle_label: 'مركبة 2', status: 'draft', status_label: 'مسودة', total: '50.00', amount_paid: '0.00', vat_rate: '15.00', due_at: null, notes: '', lines: [{ id: 22, description: 'قطعة', quantity: '1.00', unit_price: '50.00', line_total: '50.00', line_type: 'part' }] },
  { id: 3, job_card: 4, invoice_number: 'INV-3', customer_name: 'عميل 3', vehicle_label: 'مركبة 3', status: 'paid', status_label: 'مدفوعة', total: '75.00', amount_paid: '75.00', vat_rate: '15.00', due_at: null, notes: '', lines: [] },
]

const vouchers = Array.from({ length: 3 }, (_, index) => ({ id: index + 1, voucher_number: `VOC-${index + 1}`, voucher_type_label: 'سند قبض', party_name: `جهة ${index + 1}`, description: `بيان ${index + 1}`, amount: '10.00' }))
const expenses = Array.from({ length: 3 }, (_, index) => ({ id: index + 1, description: `مصروف ${index + 1}`, category: 'other', occurred_at: '2026-08-22', amount: '5.00' }))

function renderAccounting(overrides = {}) {
  const props = {
    jobs,
    invoices,
    expenses,
    vouchers,
    profitLoss: { revenue: '100', parts_cost: '20', expenses: '5', net_profit: '75' },
    expense: emptyExpense,
    setExpense: vi.fn(),
    voucher: emptyVoucher,
    setVoucher: vi.fn(),
    submit: vi.fn(),
    update: vi.fn(),
    onCreateInvoice: vi.fn(),
    onGeneratePdf: vi.fn(),
    onRecordPayment: vi.fn(),
    remove: vi.fn(),
    pageSize: 2,
    ...overrides,
  }
  render(<AccountingPage {...props} />)
  return props
}

describe('AccountingPage', () => {
  it('ينشئ الفاتورة من بطاقة غير مفوترة ويحافظ على التحصيل وPDF', () => {
    const props = renderAccounting()

    const jobSelect = screen.getByLabelText('بطاقة جاهزة أو مسلّمة')
    expect(within(jobSelect).queryByRole('option', { name: /JOB-1/ })).not.toBeInTheDocument()
    fireEvent.change(jobSelect, { target: { value: '2' } })
    fireEvent.submit(screen.getByRole('button', { name: 'إنشاء الفاتورة' }).closest('form'))
    expect(props.onCreateInvoice).toHaveBeenCalledWith('2')

    const paymentInput = screen.getByLabelText('مبلغ دفعة INV-1')
    fireEvent.change(paymentInput, { target: { value: '20.00' } })
    fireEvent.click(within(paymentInput.closest('.invoice-row')).getByRole('button', { name: 'تحصيل' }))
    expect(props.onRecordPayment).toHaveBeenCalledWith(1, '20.00')
    fireEvent.click(screen.getAllByRole('button', { name: 'PDF' })[0])
    expect(props.onGeneratePdf).toHaveBeenCalledWith(1)
  })

  it('يحافظ على تصحيح بند فاتورة المسودة', () => {
    const props = renderAccounting()

    const priceInput = screen.getAllByLabelText('سعر الوحدة')[0]
    fireEvent.change(priceInput, { target: { value: '65.00' } })
    fireEvent.submit(priceInput.closest('form'))
    expect(props.update).toHaveBeenCalledWith('/accounting/invoice-lines/22/', expect.objectContaining({ unit_price: '65.00' }), expect.any(String))
  })

  it('يقسم الفواتير والسندات والمصروفات مع الحفاظ على الحذف', () => {
    const props = renderAccounting()

    fireEvent.click(within(screen.getByRole('navigation', { name: 'تنقل صفحات فاتورة' })).getByRole('button', { name: 'التالي' }))
    expect(screen.getAllByText('INV-3').length).toBeGreaterThan(0)

    fireEvent.click(within(screen.getByRole('navigation', { name: 'تنقل صفحات سند' })).getByRole('button', { name: 'التالي' }))
    expect(screen.getByText('VOC-3')).toBeInTheDocument()

    fireEvent.click(within(screen.getByRole('navigation', { name: 'تنقل صفحات مصروف' })).getByRole('button', { name: 'التالي' }))
    fireEvent.click(within(screen.getByText('مصروف 3').closest('.record-row')).getByRole('button', { name: 'حذف' }))
    expect(props.remove).toHaveBeenCalledWith('/accounting/expenses/', 3)
  })
})
