import { Loader2, ShieldCheck } from "lucide-react";

export default function SessionLoader() {
  return (
    <div className="h-screen w-full flex flex-col items-center justify-center bg-[#F8FAFC] font-sans">
      <div className="relative flex flex-col items-center">
        <div className="absolute -z-10 h-32 w-32 bg-blue-500/10 blur-3xl rounded-full animate-pulse" />
        <div className="relative mb-6">
          <div className="h-16 w-16 bg-white border border-slate-200 rounded-[1.25rem] shadow-sm flex items-center justify-center">
            <ShieldCheck className="text-blue-600" size={32} strokeWidth={2.5} />
          </div>
          <div className="absolute -bottom-1 -right-1 bg-white p-1 rounded-full shadow-sm border border-slate-100">
            <Loader2 className="text-blue-600 animate-spin" size={18} />
          </div>
        </div>
        <div className="text-center">
          <h1 className="text-lg font-black text-slate-900 tracking-tight uppercase italic">
            Route<span className="text-blue-600">Master</span>
          </h1>
          <div className="mt-2 flex items-center gap-2 px-3 py-1 bg-blue-50/50 border border-blue-100/50 rounded-full">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            <p className="text-[10px] font-bold text-blue-700 uppercase tracking-[0.15em]">
              Securing Connection
            </p>
          </div>
        </div>

        {/* Progress Hint */}
        <p className="absolute bottom-[-60px] text-[10px] font-bold text-slate-400 uppercase tracking-widest whitespace-nowrap">
          V4.0.2 Stable Build &bull; Encrypted Session
        </p>
      </div>
    </div>
  );
}