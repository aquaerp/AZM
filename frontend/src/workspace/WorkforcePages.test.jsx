import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CommissionsPage, EmployeesPage, TasksPage } from './WorkforcePages.jsx'

const tasks = Array.from({ length: 5 }, (_, index) => ({
  id: index + 1,
  title: `مهمة ${index + 1}`,
  job_number: `JOB-${index + 1}`,
  employee_name: `فني ${index + 1}`,
  status: index === 2 ? 'in_progress' : 'not_started',
  status_label: index === 2 ? 'قيد التنفيذ' : 'لم تبدأ',
  actual_minutes: 0,
}))

const emptyTask = { job_card: '', employee: '', title: '', description: '', estimated_hours: '0.00' }
const emptyEmployee = { user: '', job_title: 'فني', hired_at: '2026-08-22', commission_rate: '0.00', notes: '' }

describe('Workforce pages', () => {
  it('يقسم المهام ويحافظ على إجراءات البدء والإكمال', () => {
    const onTaskAction = vi.fn()
    render(<TasksPage tasks={tasks} isManager={false} jobs={[]} employees={[]} task={emptyTask} setTask={vi.fn()} onSubmit={vi.fn()} onTaskAction={onTaskAction} pageSize={2} />)

    fireEvent.click(screen.getAllByRole('button', { name: 'بدء' })[0])
    expect(onTaskAction).toHaveBeenCalledWith(1, 'start')
    fireEvent.click(screen.getByRole('button', { name: 'التالي' }))
    fireEvent.click(screen.getByRole('button', { name: 'إكمال' }))
    expect(onTaskAction).toHaveBeenCalledWith(3, 'complete')
  })

  it('يقسم الموظفين ويحافظ على الحذف', () => {
    const employees = Array.from({ length: 4 }, (_, index) => ({ id: index + 1, user: index + 1, user_name: `موظف ${index + 1}`, job_title: 'فني', commission_rate: '5.00' }))
    const onDelete = vi.fn()
    render(<EmployeesPage employees={employees} team={[]} employee={emptyEmployee} setEmployee={vi.fn()} onSubmit={vi.fn()} onDelete={onDelete} pageSize={2} />)

    fireEvent.click(screen.getByRole('button', { name: 'التالي' }))
    fireEvent.click(screen.getAllByRole('button', { name: 'حذف' })[0])
    expect(onDelete).toHaveBeenCalledWith(3)
  })

  it('يعرض إجمالي كل العمولات مع ترقيم التفاصيل', () => {
    const commissions = Array.from({ length: 3 }, (_, index) => ({ id: index + 1, employee_name: `فني ${index + 1}`, job_number: `JOB-${index + 1}`, commission_rate: '10.00', basis_amount: '100.00', amount: '10.00' }))
    const onGenerate = vi.fn()
    render(<CommissionsPage commissions={commissions} onGenerate={onGenerate} pageSize={2} />)

    expect(screen.getByText('30.00 ر.س')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'احتساب الشهر الحالي' }))
    expect(onGenerate).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'التالي' }))
    expect(screen.getByText('JOB-3')).toBeInTheDocument()
  })
})
