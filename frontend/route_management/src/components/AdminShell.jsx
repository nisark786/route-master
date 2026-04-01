export default function AdminShell({ children }) {
  return (
    <div className="min-h-screen bg-[#F8FAFC] flex font-sans">
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <main className="p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
