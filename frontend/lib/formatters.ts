
export const formatCurrency = (val: unknown) => {
  if (val === null || val === undefined || val === "-") return "-";
  const num = Number(val);
  if (isNaN(num)) return "-";
  if (num === 0) return "₹0";
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)} lakh`;
  return `₹${num.toLocaleString("en-IN")}`;
};

export const humanise = (val: string | undefined) => {
  if (!val) return "-";
  return val.replace(/_/g, " ").replace(/\w/g, c => c.toUpperCase());
};
