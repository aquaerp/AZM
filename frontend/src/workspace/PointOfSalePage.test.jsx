import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PointOfSalePage from './PointOfSalePage.jsx'

const invoices = [
  { id: 1, invoice_number: 'INV-1', customer_name: 'عميل 1', vehicle_label: 'مركبة 1', status: 'issued', status_label: 'صادرة', total: '100.00', amount_paid: '20.00' },
  { id: 2, invoice_number: 'INV-2', customer_name: 'عميل 2', vehicle_label: 'مركبة 2', status: 'partially_paid', status_label: 'مدفوعة جزئياً', total: '75.00', amount_paid: '25.00' },
  { id: 3, invoice_number: 'INV-3', customer_name: 'عميل 3', vehicle_label: 'مركبة 3', status: 'issued', status_label: 'صادرة', total: '50.00', amount_paid: '0.00' },
  { id: 4, invoice_number: 'INV-4', customer_name: 'عميل 4', vehicle_label: 'مركبة 4', status: 'draft', status_label: 'مسودة', total: '30.00', amount_paid: '0.00' },
]

describe('PointOfSalePage', () => {
  it('يسجل دفعة بالوسيلة والمرجع المحددين ثم يعيد ضبط النموذج', async () => {
    const onRecordPayment = vi.fn().mockResolvedValue(true)
    render(<PointOfSalePage invoices={invoices} onRecordPayment={onRecordPayment} pageSize={2} />)

    fireEvent.change(screen.getByLabelText('الفاتورة'), { target: { value: '1' } })
    expect(screen.getByLabelText('المبلغ')).toHaveValue(80)
    fireEvent.change(screen.getByLabelText('وسيلة السداد'), { target: { value: 'transfer' } })
    fireEvent.change(screen.getByLabelText('مرجع العملية (اختياري)'), { target: { value: 'TRX-100' } })
    fireEvent.click(screen.getByRole('button', { name: 'تأكيد السداد' }))

    await waitFor(() => expect(onRecordPayment).toHaveBeenCalledWith(1, '80.00', 'transfer', 'TRX-100'))
    expect(screen.getByLabelText('الفاتورة')).toHaveValue('')
  })

  it('يعرض الفواتير القابلة للتحصيل فقط ويقسم قائمتها', () => {
    render(<PointOfSalePage invoices={invoices} onRecordPayment={vi.fn()} pageSize={2} />)

    expect(screen.queryByText('INV-4')).not.toBeInTheDocument()
    const navigation = screen.getByRole('navigation', { name: 'تنقل صفحات فاتورة نقطة بيع' })
    fireEvent.click(within(navigation).getByRole('button', { name: 'التالي' }))
    fireEvent.click(within(screen.getByText('INV-3').closest('.invoice-row')).getByRole('button', { name: 'تحصيل' }))
    expect(screen.getByLabelText('الفاتورة')).toHaveValue('3')
  })
})
