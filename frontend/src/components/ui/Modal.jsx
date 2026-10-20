import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import Button from './Button'

function ModalContent({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  footer, 
  size = 'lg',
  closeOnOverlayClick = true,
  ...props 
}) {
  const modalRef = useRef(null)
  const previousActiveElement = useRef(null)

  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement
      document.body.style.overflow = 'hidden'
      modalRef.current?.focus()
      
      const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose()
        if (e.key === 'Tab') {
          const focusableElements = modalRef.current?.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          )
          if (!focusableElements?.length) return
          
          const firstElement = focusableElements[0]
          const lastElement = focusableElements[focusableElements.length - 1]
          
          if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault()
            lastElement.focus()
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault()
            firstElement.focus()
          }
        }
      }
      
      document.addEventListener('keydown', handleKeyDown)
      return () => {
        document.removeEventListener('keydown', handleKeyDown)
        document.body.style.overflow = ''
        previousActiveElement.current?.focus()
      }
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-[90vw]',
  }

  const modal = (
    <div className="modal-overlay" onClick={closeOnOverlayClick ? onClose : undefined} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div 
        ref={modalRef}
        tabIndex={-1}
        className={`modal-content ${sizeClasses[size]}`}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2 id="modal-title" className="text-lg font-semibold text-[var(--color-text-primary)]">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="btn-ghost btn-sm p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)]"
            aria-label="Cerrar modal"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="modal-body">
          {children}
        </div>
        {footer && (
          <div className="modal-footer">
            {footer}
          </div>
        )}
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}

export default function Modal({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  footer, 
  size = 'lg',
  confirmAction,
  cancelText = 'Cancelar',
  confirmText = 'Guardar',
  loading = false,
  ...props 
}) {
  const defaultFooter = (
    <>
      <Button variant="secondary" onClick={onClose} disabled={loading}>
        {cancelText}
      </Button>
      <Button variant="primary" onClick={confirmAction} disabled={loading} loading={loading}>
        {confirmText}
      </Button>
    </>
  )

  return (
    <ModalContent
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size={size}
      footer={footer ?? defaultFooter}
      {...props}
    >
      {children}
    </ModalContent>
  )
}