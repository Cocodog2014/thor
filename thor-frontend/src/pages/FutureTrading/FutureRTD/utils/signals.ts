import type { ChipProps } from "@mui/material";
import type { SignalKey } from "../types";

export function signalLabel(sig?: SignalKey) {
  if (!sig) return "—";
  switch (sig) {
    case "STRONG_BUY":
      return "Strong Buy";
    case "BUY":
      return "Buy";
    case "HOLD":
      return "Hold";
    case "SELL":
      return "Sell";
    case "STRONG_SELL":
      return "Strong Sell";
    default:
      return "—";
  }
}

export function signalChipColor(sig?: SignalKey): ChipProps["color"] {
  if (!sig) return "default";
  switch (sig) {
    case "STRONG_BUY":
    case "BUY":
      return "success";
    case "HOLD":
      return "warning";
    case "SELL":
    case "STRONG_SELL":
      return "error";
    default:
      return "default";
  }
}
