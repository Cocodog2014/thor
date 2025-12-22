export type WsEnvelope<T = unknown> = {
  type: string;
  data?: T;
  ts?: number; // seconds since epoch
  [key: string]: unknown;
};

export type WsMessage = WsEnvelope<unknown>;

export type MessageHandler<T = unknown> = (msg: WsEnvelope<T>) => void;
export type ConnectionHandler = (connected: boolean) => void;
