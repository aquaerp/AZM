const today = new Date().toISOString().slice(0, 10)

export const emptyExpense = { category: 'other', description: '', amount: '', occurred_at: today, reference: '' }
export const emptyVoucher = { voucher_type: 'receipt', amount: '', party_name: '', description: '', reference: '', occurred_at: today, invoice: '', payment_method: 'cash', category: 'other' }
