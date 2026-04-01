import { useMemo } from "react";

import { useGetBillingTransactionsQuery } from "../../features/billing/billingApi";
import { extractApiErrorMessage } from "../../utils/adminUi";

export default function CompanySettingsBillingPage() {
  const { data, isLoading, error } = useGetBillingTransactionsQuery();
  const rows = useMemo(() => data?.results || [], [data]);
  const feedback = extractApiErrorMessage(error);

  return (
    <div className="p-8">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Billing</h1>
          <p className="text-slate-500 mt-1">View invoices and payment history.</p>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50">
            <p className="text-xs font-black uppercase tracking-wider text-slate-500">Recent Transactions</p>
          </div>

          {isLoading ? (
            <p className="p-6 text-sm text-slate-500">Loading billing transactions...</p>
          ) : feedback ? (
            <p className="p-6 text-sm text-rose-600">{feedback}</p>
          ) : !rows.length ? (
            <p className="p-6 text-sm text-slate-500">No transactions found.</p>
          ) : (
            <div className="overflow-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-4 py-3 text-left font-black uppercase text-[10px] tracking-wider">Invoice</th>
                    <th className="px-4 py-3 text-left font-black uppercase text-[10px] tracking-wider">Plan</th>
                    <th className="px-4 py-3 text-left font-black uppercase text-[10px] tracking-wider">Amount</th>
                    <th className="px-4 py-3 text-left font-black uppercase text-[10px] tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left font-black uppercase text-[10px] tracking-wider">Paid At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((row) => (
                    <tr key={row.id}>
                      <td className="px-4 py-3 font-bold text-slate-900">{row.invoice_number || "-"}</td>
                      <td className="px-4 py-3 text-slate-700">{row.plan_code || "-"}</td>
                      <td className="px-4 py-3 text-slate-700">
                        {row.currency} {row.amount}
                      </td>
                      <td className="px-4 py-3 text-slate-700">{row.status}</td>
                      <td className="px-4 py-3 text-slate-700">
                        {row.paid_at ? new Date(row.paid_at).toLocaleString() : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
