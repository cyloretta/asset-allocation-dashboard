import { useState, useEffect, useCallback, createContext, useContext, memo } from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastContextType {
  showToast: (type: ToastType, message: string, duration?: number) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
  warning: (message: string, duration?: number) => void;
  info: (message: string, duration?: number) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

let toastId = 0;

const TOAST_STYLES: Record<ToastType, { bg: string; border: string; text: string; glow: string }> = {
  success: {
    bg: 'bg-neon-green/10',
    border: 'border-neon-green/40',
    text: 'text-neon-green',
    glow: '0 0 20px rgba(0, 255, 136, 0.3)',
  },
  error: {
    bg: 'bg-status-loss/10',
    border: 'border-status-loss/40',
    text: 'text-status-loss',
    glow: '0 0 20px rgba(255, 51, 102, 0.3)',
  },
  warning: {
    bg: 'bg-status-warning/10',
    border: 'border-status-warning/40',
    text: 'text-status-warning',
    glow: '0 0 20px rgba(255, 170, 0, 0.3)',
  },
  info: {
    bg: 'bg-neon-cyan/10',
    border: 'border-neon-cyan/40',
    text: 'text-neon-cyan',
    glow: '0 0 20px rgba(0, 245, 255, 0.3)',
  },
};

const TOAST_ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 className="w-5 h-5" />,
  error: <AlertCircle className="w-5 h-5" />,
  warning: <AlertTriangle className="w-5 h-5" />,
  info: <Info className="w-5 h-5" />,
};

const ToastItem = memo(function ToastItem({
  toast,
  onClose,
}: {
  toast: ToastItem;
  onClose: (id: number) => void;
}) {
  const styles = TOAST_STYLES[toast.type];

  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const timer = setTimeout(() => onClose(toast.id), toast.duration);
      return () => clearTimeout(timer);
    }
  }, [toast.id, toast.duration, onClose]);

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl ${styles.bg} ${styles.border} animate-slide-in`}
      style={{ boxShadow: styles.glow }}
    >
      <span className={styles.text}>{TOAST_ICONS[toast.type]}</span>
      <span className={`flex-1 text-sm font-mono ${styles.text}`}>{toast.message}</span>
      <button
        onClick={() => onClose(toast.id)}
        className={`${styles.text} hover:opacity-70 transition-opacity`}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
});

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const showToast = useCallback((type: ToastType, message: string, duration = 4000) => {
    const id = ++toastId;
    setToasts(prev => [...prev, { id, type, message, duration }]);
  }, []);

  const success = useCallback((message: string, duration?: number) => showToast('success', message, duration), [showToast]);
  const error = useCallback((message: string, duration?: number) => showToast('error', message, duration), [showToast]);
  const warning = useCallback((message: string, duration?: number) => showToast('warning', message, duration), [showToast]);
  const info = useCallback((message: string, duration?: number) => showToast('info', message, duration), [showToast]);

  return (
    <ToastContext.Provider value={{ showToast, success, error, warning, info }}>
      {children}
      {/* Toast Container */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map(toast => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} onClose={removeToast} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export default ToastProvider;
