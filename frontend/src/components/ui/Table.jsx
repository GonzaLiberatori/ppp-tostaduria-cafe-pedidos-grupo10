import { forwardRef } from 'react'

const Table = forwardRef(({ 
  columns = [], 
  data = [], 
  keyField = 'id', 
  onRowClick, 
  emptyMessage = 'No hay datos disponibles',
  className = '',
  ...props 
}, ref) => {
  return (
    <div className={`table-container ${className}`} ref={ref} {...props}>
      {data.length > 0 ? (
        <table className="table" role="grid">
          <thead>
            <tr>
              {columns.map((col, index) => (
                <th key={col.key || index} scope="col" style={{ width: col.width }}>
                  {col.header}
                </th>
              ))}
              {onRowClick && <th scope="col" style={{ width: '48px' }}>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr 
                key={row[keyField]} 
                onClick={() => onRowClick?.(row)}
                className={onRowClick ? 'cursor-pointer' : ''}
              >
                {columns.map((col, colIndex) => (
                  <td key={col.key || colIndex}>
                    {col.render ? col.render(row[col.key], row) : row[col.key]}
                  </td>
                ))}
                {onRowClick && (
                  <td className="text-center">
                    <svg className="w-5 h-5 mx-auto text-coffee-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                    </svg>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="empty-state">
          <svg className="empty-state-icon w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="empty-state-title">Sin resultados</p>
          <p className="empty-state-description">{emptyMessage}</p>
        </div>
      )}
    </div>
  )
})

Table.displayName = 'Table'

export default Table