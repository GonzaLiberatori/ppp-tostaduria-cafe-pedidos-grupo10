import { forwardRef } from 'react'

const Select = forwardRef(({ 
  label, 
  error, 
  help, 
  options = [], 
  placeholder = 'Seleccionar...',
  className = '', 
  id, 
  ...props 
}, ref) => {
  const selectId = id || label?.toLowerCase().replace(/\s+/g, '-')
  const errorId = `${selectId}-error`
  const helpId = `${selectId}-help`

  return (
    <div className="form-group">
      {label && (
        <label htmlFor={selectId} className="label">
          {label}
        </label>
      )}
      <select
        ref={ref}
        id={selectId}
        className={`select ${error ? 'input-error' : ''} ${className}`}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? errorId : help ? helpId : undefined}
        {...props}
      >
        <option value="" disabled>{placeholder}</option>
        {options.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <p id={errorId} className="form-error" role="alert">
          {error}
        </p>
      )}
      {help && !error && (
        <p id={helpId} className="form-help">
          {help}
        </p>
      )}
    </div>
  )
})

Select.displayName = 'Select'

export default Select