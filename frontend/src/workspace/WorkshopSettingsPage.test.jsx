import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { emptyWorkshopProfile } from './WorkshopSettingsDefaults.js'
import WorkshopSettingsPage from './WorkshopSettingsPage.jsx'

describe('WorkshopSettingsPage', () => {
  it('يحافظ على تحديث بيانات الورشة وخيار التسليم الآلي والحفظ', () => {
    const setProfile = vi.fn()
    const setLogo = vi.fn()
    const onSubmit = vi.fn((event) => event.preventDefault())
    const profile = { ...emptyWorkshopProfile, name: 'عزم', legal_name: 'شركة عزم', tax_number: '123456789012345', phone: '0500000000', city: 'الرياض', district: 'الياسمين', street: 'الملك', building_number: '10', postal_code: '12345' }
    render(<WorkshopSettingsPage profile={profile} setProfile={setProfile} logo={null} setLogo={setLogo} onSubmit={onSubmit} />)

    fireEvent.change(screen.getByLabelText('اسم الورشة'), { target: { value: 'عزم الجديدة' } })
    expect(setProfile).toHaveBeenCalledWith(expect.objectContaining({ name: 'عزم الجديدة' }))
    fireEvent.click(screen.getByLabelText(/تسليم البطاقة الجاهزة آليًا/))
    expect(setProfile).toHaveBeenCalledWith(expect.objectContaining({ auto_deliver_paid_ready_jobs: true }))
    fireEvent.click(screen.getByRole('button', { name: 'حفظ إعدادات الورشة' }))
    expect(onSubmit).toHaveBeenCalled()
  })
})
