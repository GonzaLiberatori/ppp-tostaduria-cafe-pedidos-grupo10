const Badge = ({ 
  children, 
  variant = 'default', 
  className = '', 
  dot = false,
  ...props 
}) => {
  const variantClasses = {
    default: 'badge-coffee',
    success: 'badge-success',
    warning: 'badge-warning',
    danger: 'badge-danger',
    info: 'badge-info',
    coffee: 'badge-coffee',
  }

  return (
    <span className={`${variantClasses[variant]} ${className}`} {...props}>
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5" aria-hidden="true" />}
      {children}
    </span>
  )
}

export default Badge