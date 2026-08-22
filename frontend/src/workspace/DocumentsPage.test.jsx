import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DocumentsPage from './DocumentsPage.jsx'

const documents = Array.from({ length: 3 }, (_, index) => ({ id: index + 1, name: `وثيقة ${index + 1}`, document_type: 'رخصة', owner_label: 'الورشة', expires_at: null, original_filename: `doc-${index + 1}.pdf` }))
const alerts = Array.from({ length: 3 }, (_, index) => ({ id: index + 1, document_name: `تنبيه ${index + 1}`, expires_at: '2026-09-01', days_before: 10, acknowledged_at: null }))

function renderDocuments(overrides = {}) {
  const props = {
    documents,
    alerts,
    customers: [{ id: 7, name: 'عميل تجريبي' }],
    vehicles: [],
    employees: [],
    onUpload: vi.fn(),
    onDownload: vi.fn(),
    onAcknowledge: vi.fn(),
    remove: vi.fn(),
    pageSize: 2,
    ...overrides,
  }
  render(<DocumentsPage {...props} />)
  return props
}

describe('DocumentsPage', () => {
  it('يرفع وثيقة مرتبطة بعميل ضمن FormData', () => {
    const props = renderDocuments()
    fireEvent.change(screen.getByLabelText('اسم الوثيقة'), { target: { value: 'عقد صيانة' } })
    fireEvent.change(screen.getByLabelText('نوع الوثيقة'), { target: { value: 'عقد' } })
    fireEvent.change(screen.getByLabelText('ربط بـ'), { target: { value: 'customer' } })
    fireEvent.change(screen.getByLabelText('الجهة'), { target: { value: '7' } })
    const file = new File(['contract'], 'contract.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('الملف'), { target: { files: [file] } })
    fireEvent.submit(screen.getByRole('button', { name: 'رفع وتشفير الوثيقة' }).closest('form'))

    const data = props.onUpload.mock.calls[0][0]
    expect(data.get('name')).toBe('عقد صيانة')
    expect(data.get('customer')).toBe('7')
    expect(data.get('file')).toBe(file)
  })

  it('يقسم التنبيهات والوثائق ويحافظ على إجراءاتها', () => {
    const props = renderDocuments()
    fireEvent.click(within(screen.getByRole('navigation', { name: 'تنقل صفحات تنبيه وثيقة' })).getByRole('button', { name: 'التالي' }))
    fireEvent.click(within(screen.getByText('تنبيه 3').closest('.record-row')).getByRole('button', { name: 'تأكيد' }))
    expect(props.onAcknowledge).toHaveBeenCalledWith(3)

    fireEvent.click(within(screen.getByRole('navigation', { name: 'تنقل صفحات وثيقة' })).getByRole('button', { name: 'التالي' }))
    const row = screen.getByText('وثيقة 3').closest('.document-row')
    fireEvent.click(within(row).getByRole('button', { name: 'تنزيل' }))
    fireEvent.click(within(row).getByRole('button', { name: 'حذف' }))
    expect(props.onDownload).toHaveBeenCalledWith(documents[2])
    expect(props.remove).toHaveBeenCalledWith('/documents/documents/', 3)
  })
})
