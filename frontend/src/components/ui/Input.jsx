import { forwardRef } from 'react'

const Input = forwardRef(({ 
  label, 
  error, 
  help, 
  className = '', 
  id, 
  ...props 
}, ref) => {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
  const errorId = `${inputId}-error`
  const helpId = `${inputId}-help`

  return (
    <div className="form-group">
      {label && (
        <label htmlFor={inputId} className="label">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={`input ${error ? 'input-error' : ''} ${className}`}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? errorId : help ? helpId : undefined}
        {...props}
      />
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

Input.displayName = 'Input'

export default Input