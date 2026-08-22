import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import InventoryPage from './InventoryPage.jsx'

const suppliers = Array.from({ length: 3 }, (_, index) => ({ id: index + 1, name: `مورد ${index + 1}`, contact_name: '', phone: '', email: '' }))
const parts = Array.from({ length: 3 }, (_, index) => ({ id: index + 1, name: `قطعة ${index + 1}`, sku: `SKU-${index + 1}`, quantity: 5, reorder_level: 2, sale_price: '10.00', supplier_name: 'مورد', is_active: true, is_low_stock: false }))
const partRequests = Array.from({ length: 3 }, (_, index) => ({ id: index + 1, job_number: `JOB-${index + 1}`, part_name: `قطعة ${index + 1}`, requested_by_name: 'فني', quantity: 1, status: 'requested', status_label: 'مطلوب' }))
const jobs = [{ id: 1, job_number: 'JOB-1', vehicle_label: 'مركبة', status: 'in_progress' }]
const emptySupplier = { name: '', contact_name: '', phone: '', email: '', notes: '' }
const emptyPart = { name: '', sku: '', supplier: '', quantity: '0', reorder_level: '0', purchase_price: '0.00', sale_price: '0.00' }
const emptyUsage = { job_card: '', part: '', quantity: '1' }
const emptyRequest = { job_card: '', part: '', quantity: '1', notes: '' }

function renderInventory(overrides = {}) {
  const props = {
    suppliers,
    parts,
    lowStock: [],
    alerts: [],
    partUsages: [],
    partRequests,
    jobs,
    supplier: emptySupplier,
    setSupplier: vi.fn(),
    part: emptyPart,
    setPart: vi.fn(),
    partUsage: emptyUsage,
    setPartUsage: vi.fn(),
    partRequest: emptyRequest,
    setPartRequest: vi.fn(),
    onSaveSupplier: vi.fn(),
    onCancelSupplier: vi.fn(),
    onSubmitPart: vi.fn(),
    onSubmitUsage: vi.fn(),
    onSubmitRequest: vi.fn(),
    onDeleteSupplier: vi.fn(),
    onDeletePart: vi.fn(),
    onAcknowledge: vi.fn(),
    onReviewRequest: vi.fn(),
    canManage: false,
    canIssue: false,
    isTechnician: false,
    pageSize: 2,
    ...overrides,
  }
  render(<InventoryPage {...props} />)
  return props
}

describe('InventoryPage', () => {
  it('يسمح للفني بإرسال الطلب دون إظهار إجراءات الصرف', () => {
    const props = renderInventory({ isTechnician: true })

    fireEvent.submit(screen.getByRole('button', { name: 'إرسال الطلب' }).closest('form'))
    expect(props.onSubmitRequest).toHaveBeenCalledOnce()
    expect(screen.queryByRole('button', { name: 'صرف' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'رفض' })).not.toBeInTheDocument()
  })

  it('يقسم طلبات القطع ويحافظ على الصرف والرفض للمخول', () => {
    const props = renderInventory({ canIssue: true })

    fireEvent.click(screen.getAllByRole('button', { name: 'صرف' })[0])
    expect(props.onReviewRequest).toHaveBeenCalledWith(1, 'fulfill')
    fireEvent.click(screen.getAllByRole('button', { name: 'رفض' })[0])
    expect(props.onReviewRequest).toHaveBeenCalledWith(1, 'reject')

    const requestNavigation = screen.getByRole('navigation', { name: 'تنقل صفحات طلب' })
    fireEvent.click(within(requestNavigation).getByRole('button', { name: 'التالي' }))
    expect(screen.getByText(/JOB-3/)).toBeInTheDocument()
  })

  it('يقسم الموردين ويحافظ على التعديل والحذف والتنبيه', () => {
    const alerts = [{ id: 1, is_active: true, part_sku: 'LOW-1', part_name: 'منخفضة', quantity_at_alert: 1 }]
    const props = renderInventory({ canManage: true, alerts })

    const supplierNavigation = screen.getByRole('navigation', { name: 'تنقل صفحات مورد' })
    fireEvent.click(within(supplierNavigation).getByRole('button', { name: 'التالي' }))
    fireEvent.click(screen.getByRole('button', { name: 'تعديل' }))
    expect(props.setSupplier).toHaveBeenCalledWith(suppliers[2])
    fireEvent.click(screen.getAllByRole('button', { name: 'حذف' })[0])
    expect(props.onDeleteSupplier).toHaveBeenCalledWith(3)
    fireEvent.click(screen.getByRole('button', { name: 'تأكيد الاطلاع' }))
    expect(props.onAcknowledge).toHaveBeenCalledWith(1)
  })
})
