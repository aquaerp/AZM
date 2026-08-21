import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RecordsPage from './RecordsPage.jsx'

const items = Array.from({ length: 7 }, (_, index) => ({ id: index + 1, name: `سجل ${index + 1}` }))

describe('RecordsPage', () => {
  it('يعرض السجلات على صفحات ويحافظ على إجراءات الصف', () => {
    const onDelete = vi.fn()
    render(<RecordsPage title="العملاء" form={<form aria-label="نموذج العميل" />} items={items} columns={(item) => <strong>{item.name}</strong>} onDelete={onDelete} pageSize={3} />)

    expect(screen.getByText('سجل 1')).toBeInTheDocument()
    expect(screen.queryByText('سجل 4')).not.toBeInTheDocument()
    expect(screen.getByText('صفحة 1 من 3')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'التالي' }))
    expect(screen.queryByText('سجل 1')).not.toBeInTheDocument()
    expect(screen.getByText('سجل 4')).toBeInTheDocument()
    expect(screen.getByText('صفحة 2 من 3')).toBeInTheDocument()

    fireEvent.click(screen.getAllByRole('button', { name: 'حذف' })[0])
    expect(onDelete).toHaveBeenCalledWith(4)
  })

  it('لا يعرض أدوات التنقل عندما تكفي صفحة واحدة', () => {
    render(<RecordsPage title="الخدمات" form={<form />} items={items.slice(0, 2)} columns={(item) => <strong>{item.name}</strong>} pageSize={3} />)

    expect(screen.queryByRole('navigation', { name: 'تنقل صفحات سجل' })).not.toBeInTheDocument()
  })
})
