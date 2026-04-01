export default function AdminModal({
  isOpen,
  title,
  description = "",
  onClose,
  children,
  maxWidthClass = "max-w-3xl",
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[1px]">
      <div className={`flex max-h-[calc(100vh-2rem)] w-full flex-col ${maxWidthClass} rounded-2xl border border-slate-200 bg-white shadow-xl`}>
        <div className="shrink-0 flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
          <div>
            <h3 className="text-base font-black text-slate-900">{title}</h3>
            {description ? <p className="mt-1 text-sm text-slate-600">{description}</p> : null}
          </div>
          <button
            type="button"
            className="rounded-lg px-2 py-1 text-xs font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <div className="min-h-0 overflow-y-auto px-6 py-5">{children}</div>
      </div>
    </div>
  );
}
