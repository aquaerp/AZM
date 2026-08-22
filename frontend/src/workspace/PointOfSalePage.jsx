import { useState } from 'react'
import Pagination from './Pagination.jsx'
import { usePagination } from './usePagination.js'

export default function PointOfSalePage({ invoices, onRecordPayment, pageSize }) {
  const payableInvoices = invoices.filter((item) => !['paid', 'void', 'draft'].includes(item.status))
  const pagination = usePagination(payableInvoices, pageSize)
  const [invoiceId, setInvoiceId] = useState('')
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('card')
  const [reference, setReference] = useState('')
  const selectedInvoice = payableInvoices.find((item) => item.id === Number(invoiceId))
  const remaining = selectedInvoice ? Math.max(0, Number(selectedInvoice.total) - Number(selectedInvoice.amount_paid)) : 0

  const selectInvoice = (value) => {
    setInvoiceId(value)
    const invoice = payableInvoices.find((item) => item.id === Number(value))
    setAmount(invoice ? Math.max(0, Number(invoice.total) - Number(invoice.amount_paid)).toFixed(2) : '')
  }

  const submitPayment = async (event) => {
    event.preventDefault()
    if (!selectedInvoice || !amount || Number(amount) <= 0 || Number(amount) > remaining) return
    const paid = await onRecordPayment(selectedInvoice.id, amount, method, reference)
    if (paid) {
      setInvoiceId('')
      setAmount('')
      setReference('')
    }
  }

  return <>
    <section className="dashboard-intro"><div><h2>نقطة البيع</h2><p>سجّل سداد الفاتورة فوراً من النقد أو البطاقة أو التحويل، وسيتم تحديث رصيدها وحالتها.</p></div></section>
    <section className="form-card"><form className="entry-form" onSubmit={submitPayment}><label>الفاتورة<select required value={invoiceId} onChange={(event) => selectInvoice(event.target.value)}><option value="">اختر الفاتورة</option>{payableInvoices.map((item) => <option value={item.id} key={item.id}>{item.invoice_number} — {item.customer_name} — المتبقي {Math.max(0, Number(item.total) - Number(item.amount_paid)).toFixed(2)} ر.س</option>)}</select></label><label>وسيلة السداد<select value={method} onChange={(event) => setMethod(event.target.value)}><option value="card">بطاقة مدى/ائتمانية</option><option value="cash">نقدي</option><option value="transfer">تحويل بنكي</option><option value="other">أخرى</option></select></label><label>المبلغ<input required type="number" min="0.01" max={remaining || undefined} step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} /></label><label>مرجع العملية (اختياري)<input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="رقم العملية أو آخر أرقام البطاقة" /></label><button className="primary" disabled={!selectedInvoice || !amount}>تأكيد السداد</button></form></section>
    {selectedInvoice && <section className="financial-grid"><article><span>إجمالي الفاتورة</span><strong>{Number(selectedInvoice.total).toFixed(2)} ر.س</strong></article><article><span>المسدد سابقاً</span><strong>{Number(selectedInvoice.amount_paid).toFixed(2)} ر.س</strong></article><article className="positive"><span>المتبقي للتحصيل</span><strong>{remaining.toFixed(2)} ر.س</strong></article></section>}
    <section className="recent-jobs">
      <div className="section-heading"><h2>فواتير بانتظار السداد</h2><span>{payableInvoices.length} فاتورة</span></div>
      {payableInvoices.length ? <div className="record-list">{pagination.pageItems.map((item) => <div className="invoice-row" key={item.id}><div><strong>{item.invoice_number}</strong><small>{item.customer_name} · {item.vehicle_label}</small></div><span className="job-status">{item.status_label}</span><strong>{Math.max(0, Number(item.total) - Number(item.amount_paid)).toFixed(2)} ر.س</strong><button className="text-action" type="button" onClick={() => selectInvoice(String(item.id))}>تحصيل</button></div>)}</div> : <p className="empty-state">لا توجد فواتير جاهزة للتحصيل.</p>}
      <Pagination {...pagination} onPageChange={pagination.setPage} itemLabel="فاتورة نقطة بيع" />
    </section>
  </>
}
