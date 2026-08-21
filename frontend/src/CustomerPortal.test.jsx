import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CustomerPortal from './CustomerPortal'
import api from './api'

vi.mock('./api', () => ({
  default: { get: vi.fn() },
}))

const token = 'c3f962cc-af1d-4ae6-a9bb-fd39ae1b2072'

describe('CustomerPortal', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows only the customer-safe job status and invoice summary', async () => {
    api.get.mockResolvedValue({
      data: {
        job_number: 'JC-000001',
        vehicle: 'Toyota Camry - ABC 123',
        status: 'ready',
        status_label: 'جاهزة للاستلام',
        received_at: '2026-08-01T09:00:00Z',
        promised_at: null,
        invoice: { status_label: 'صادرة', total: '138.00', amount_paid: '0.00' },
      },
    })

    render(<CustomerPortal token={token} language="en" onLanguageChange={vi.fn()} />)

    expect(await screen.findByText('Toyota Camry - ABC 123')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('JC-000001')
    expect(screen.getByText('138.00', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('Ready for pickup')).toBeInTheDocument()
    expect(screen.getByText('Vehicle')).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith(`/portal/jobs/${token}/`)
  })

  it('shows an error state when the public link is invalid', async () => {
    api.get.mockRejectedValue(new Error('Not found'))

    render(<CustomerPortal token={token} language="en" onLanguageChange={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Unable to open tracking')
    })
    expect(api.get).toHaveBeenCalledWith(`/portal/jobs/${token}/`)
  })

})
