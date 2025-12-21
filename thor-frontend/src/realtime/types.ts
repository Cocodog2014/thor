export type WsMessage = {
  type: string;
  [key: string]: unknown;
};

export type MessageHandler = (msg: WsMessage) => void;
export type ConnectionHandler = (connected: boolean) => void;
