import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import LanguageToggle from './LanguageToggle'

describe('LanguageToggle', () => {
  it('switches from Arabic to English', () => {
    const onChange = vi.fn()
    render(<LanguageToggle language="ar" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'Switch to English' }))
    expect(onChange).toHaveBeenCalledWith('en')
  })
})
