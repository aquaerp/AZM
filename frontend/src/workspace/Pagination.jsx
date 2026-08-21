function Pagination({ currentPage, endIndex, onPageChange, startIndex, totalItems, totalPages, itemLabel = 'سجل' }) {
  if (totalPages <= 1) return null

  return <nav className="pagination" aria-label={`تنقل صفحات ${itemLabel}`}>
    <span>عرض {startIndex + 1}–{endIndex} من {totalItems} {itemLabel}</span>
    <div className="pagination-actions">
      <button type="button" className="subtle" disabled={currentPage === 1} onClick={() => onPageChange(currentPage - 1)}>السابق</button>
      <strong aria-live="polite">صفحة {currentPage} من {totalPages}</strong>
      <button type="button" className="subtle" disabled={currentPage === totalPages} onClick={() => onPageChange(currentPage + 1)}>التالي</button>
    </div>
  </nav>
}

export default Pagination
