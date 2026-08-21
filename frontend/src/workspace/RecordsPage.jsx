import Pagination from './Pagination.jsx'
import { usePagination } from './usePagination.js'

function RecordsPage({ title, form, items, columns, onDelete, pageSize }) {
  const pagination = usePagination(items, pageSize)

  return <>
    <section className="dashboard-intro"><div><h2>{title}</h2><p>أضف البيانات لتصبح متاحة عند فتح بطاقات العمل.</p></div></section>
    <section className="form-card">{form}</section>
    <section className="recent-jobs">
      <div className="section-heading"><h2>السجلات</h2><span>{items.length} سجل</span></div>
      {items.length ? <>
        <div className="record-list">{pagination.pageItems.map((item) => <div className="record-row" key={item.id}>{columns(item)}{onDelete && <button className="delete-action" type="button" onClick={() => onDelete(item.id)}>حذف</button>}</div>)}</div>
        <Pagination {...pagination} onPageChange={pagination.setPage} itemLabel="سجل" />
      </> : <p className="empty-state">لا توجد سجلات بعد.</p>}
    </section>
  </>
}

export default RecordsPage
