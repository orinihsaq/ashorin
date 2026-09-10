import React from 'react';
import { WarningCircle, X } from '@phosphor-icons/react';

interface ErrorAlertProps {
  message: string | null;
  onDismiss: () => void;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({ message, onDismiss }) => {
  if (!message) return null;

  return (
    <div className="flex items-start gap-3 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-rose-800 dark:text-rose-200 shadow-sm animate-in fade-in duration-200">
      <WarningCircle size={20} weight="fill" className="text-rose-500 shrink-0 mt-0.5" />
      <div className="flex-1 text-xs sm:text-sm">
        <p className="font-semibold mb-0.5">Extraction Notice</p>
        <p className="text-rose-700 dark:text-rose-300">{message}</p>
      </div>
      <button
        onClick={onDismiss}
        className="p-1 rounded-md text-rose-500 hover:text-rose-700 dark:hover:text-rose-200 hover:bg-rose-100 dark:hover:bg-rose-900/50 transition shrink-0"
        title="Dismiss error"
        aria-label="Dismiss error"
      >
        <X size={16} />
      </button>
    </div>
  );
};
