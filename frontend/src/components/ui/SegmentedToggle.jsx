export default function SegmentedToggle({ value, onChange, options = [], label, className = '' }) {
  return (
    <div className={className}>
      {label && <span className="label">{label}</span>}
      <div
        role="radiogroup"
        aria-label={label}
        className="inline-flex w-full gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-tertiary)] p-1"
      >
        {options.map(option => {
          const activo = option.value === value
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={activo}
              onClick={() => onChange(option.value)}
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coffee-500 ${
                activo
                  ? 'bg-coffee-500 text-white shadow-sm'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)]'
              }`}
            >
              {option.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
