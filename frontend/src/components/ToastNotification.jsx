/**
 * ToastNotification.jsx
 *
 * Fixed top-right stack of auto-dismissing banners.
 * Props:
 *   toasts   — array of { id, message, type }
 *   onDismiss(id) — callback to remove a toast
 * Types: 'success' (green) | 'warning' (yellow) | 'error' (red)
 * Auto-dismissed after 5 s by the parent via addToast.
 */
import React, { useEffect } from 'react';

const TYPE_STYLES = {
  success: 'bg-green-900/90 border-green-500/50 text-green-200',
  warning: 'bg-yellow-900/90 border-yellow-500/50 text-yellow-200',
  error:   'bg-red-900/90   border-red-500/50   text-red-200',
};

const TYPE_ICONS = {
  success: '✓',
  warning: '⚠',
  error:   '✕',
};

export default function ToastNotification({ toasts, onDismiss }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[200] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg pointer-events-auto
            ${TYPE_STYLES[toast.type] || TYPE_STYLES.success}`}
        >
          <span className="text-sm font-bold shrink-0 mt-0.5">
            {TYPE_ICONS[toast.type] || TYPE_ICONS.success}
          </span>
          <span className="text-sm flex-1 leading-snug">{toast.message}</span>
          <button
            onClick={() => onDismiss(toast.id)}
            aria-label="Dismiss"
            className="shrink-0 opacity-60 hover:opacity-100 text-base leading-none ml-1"
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
}
