import React, { useEffect, useMemo, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSelectedAccount } from "../context/SelectedAccountContext";
import { qk } from "./queryKeys";
import type { ThorEvent, ThorTopic } from "./events";

type Sub = { topic: ThorTopic; accountId?: string; accountKey?: string };

type RealTimeProviderProps = {
  children: React.ReactNode;
};

export const RealTimeProvider: React.FC<RealTimeProviderProps> = ({ children }) => {
  const { accountId, accountKey } = useSelectedAccount();
  const qc = useQueryClient();

  const wsRef = useRef<WebSocket | null>(null);

  const wsUrl = useMemo(() => import.meta.env.VITE_WS_URL ?? null, []);

  useEffect(() => {
    if (!wsUrl) return; // no-op until configured
    if (!accountKey) return;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      const subs: Sub[] = [
        { topic: "balances", accountId: accountId ?? undefined, accountKey },
        { topic: "positions", accountId: accountId ?? undefined, accountKey },
        { topic: "activityToday", accountId: accountId ?? undefined, accountKey },
      ];
      ws.send(JSON.stringify({ action: "subscribe", subs }));
    };

    ws.onmessage = (evt) => {
      let msg: ThorEvent;
      try {
        msg = JSON.parse(evt.data);
      } catch {
        return;
      }

      if (msg.accountId && accountId && String(msg.accountId) !== String(accountId)) return;

      const keyFor = (topic: ThorTopic) => {
        switch (topic) {
          case "balances":
            return qk.balances(accountKey);
          case "positions":
            return qk.positions(accountKey);
          case "activityToday":
            return qk.activityToday(accountKey);
          case "orders":
            return qk.orders(accountKey);
          case "quotes":
            return qk.quotes(accountKey);
        }
      };

      if (msg.type === "snapshot") {
        qc.setQueryData(keyFor(msg.topic), msg.payload);
      } else if (msg.type === "patch") {
        qc.setQueryData(keyFor(msg.topic), (prev: unknown) => {
          if (msg.merge === "shallow" && prev && typeof prev === "object") {
            return { ...(prev as Record<string, unknown>), ...msg.payload };
          }
          return msg.payload;
        });
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return () => ws.close();
  }, [wsUrl, accountId, accountKey, qc]);

  return <>{children}</>;
};
