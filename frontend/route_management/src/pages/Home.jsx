import { Link } from "react-router-dom";
import { ArrowRight, Truck, LayoutGrid, Activity, ShieldCheck } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] font-sans text-slate-900">
      <main className="max-w-5xl mx-auto px-6 py-20">
        {/* Hero Section - Centered & Minimal */}
        <div className="text-center mb-20">
          <h1 className="text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Streamline your logistics <br />
            <span className="text-blue-600 font-black">infrastructure.</span>
          </h1>
          <p className="mt-6 text-lg text-slate-500 max-w-2xl mx-auto leading-relaxed">
            A unified platform to manage companies, track high-performance routes, and 
            automate subscription lifecycles with enterprise-grade security.
          </p>
          <div className="mt-10 flex justify-center gap-4">
            
          </div>
        </div>

       

      
      </main>
    </div>
  );
}