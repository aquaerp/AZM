import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { JobList } from './JobPages.jsx'

const jobs = Array.from({ length: 5 }, (_, index) => ({
  id: index + 1,
  job_number: `JOB-${index + 1}`,
  vehicle_label: `مركبة ${index + 1}`,
  customer_name: `عميل ${index + 1}`,
  complaint: `عطل ${index + 1}`,
  promised_at: null,
  status: 'pending',
  status_label: 'بانتظار الفحص',
}))

describe('JobList', () => {
  it('يقسم البطاقات مع إبقاء إجراء تحديث الحالة', () => {
    const onStatus = vi.fn()
    render(<JobList jobs={jobs} pageSize={2} onStatus={onStatus} canChangeStatus />)

    expect(screen.getByText('JOB-1')).toBeInTheDocument()
    expect(screen.queryByText('JOB-3')).not.toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'بدء العمل' })[0])
    expect(onStatus).toHaveBeenCalledWith(1, 'in_progress')

    fireEvent.click(screen.getByRole('button', { name: 'التالي' }))
    expect(screen.getByText('JOB-3')).toBeInTheDocument()
    expect(screen.getByText('صفحة 2 من 3')).toBeInTheDocument()
  })
})
