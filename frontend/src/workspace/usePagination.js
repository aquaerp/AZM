import { useEffect, useState } from 'react'

export const DEFAULT_PAGE_SIZE = 10

export function usePagination(items, pageSize = DEFAULT_PAGE_SIZE) {
  const [page, setPage] = useState(1)
  const totalItems = items.length
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const currentPage = Math.min(page, totalPages)
  const startIndex = (currentPage - 1) * pageSize
  const endIndex = Math.min(startIndex + pageSize, totalItems)

  useEffect(() => {
    setPage((value) => Math.min(value, totalPages))
  }, [totalPages])

  return {
    currentPage,
    endIndex,
    pageItems: items.slice(startIndex, endIndex),
    setPage,
    startIndex,
    totalItems,
    totalPages,
  }
}
