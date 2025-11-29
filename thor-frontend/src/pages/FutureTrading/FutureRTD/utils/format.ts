export function fmt(n: string | number | null | undefined, dp = 2): string {
  if (n === null || n === undefined) return "—";
  const num = typeof n === "string" ? Number(n) : n;
  if (Number.isNaN(num)) return "—";
  return num.toLocaleString("en-US", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
}
