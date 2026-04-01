export function formatCurrency(value) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function extractApiErrorMessage(error, fallback = "") {
  if (!error) return "";
  const details = error?.error?.details;
  if (details && typeof details === "object") {
    const firstValue = Object.values(details)[0];
    if (typeof firstValue === "string") return firstValue;
    if (Array.isArray(firstValue) && firstValue[0]) return String(firstValue[0]);
  }
  return (
    error?.message ||
    error?.error?.details?.detail ||
    error?.error?.details?.error ||
    error?.error?.details?.non_field_errors?.[0] ||
    fallback
  );
}

export function extractApiSuccessMessage(response) {
  if (!response) return "";
  if (typeof response?.message === "string" && response.message.trim()) return response.message;
  if (typeof response?.detail === "string" && response.detail.trim()) return response.detail;
  return "";
}

export function localDateTimeInputToIso(value) {
  if (!value) return "";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "";
  return dt.toISOString();
}

export function isoToLocalDateTimeInput(value) {
  if (!value) return "";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "";
  const year = dt.getFullYear();
  const month = String(dt.getMonth() + 1).padStart(2, "0");
  const day = String(dt.getDate()).padStart(2, "0");
  const hour = String(dt.getHours()).padStart(2, "0");
  const minute = String(dt.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hour}:${minute}`;
}
