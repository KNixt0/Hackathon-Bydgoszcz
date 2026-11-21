import { io } from "socket.io-client";
import type { ScanJob } from "../types/api";
import type { IncidentSummary } from "../types/incident";

export interface ServerEvents {
  "incident:new": IncidentSummary;
  "incident:updated": IncidentSummary;
  "alert:high": IncidentSummary;
  "scan:progress": ScanJob;
}
export type ServerEventName = keyof ServerEvents;

/** The minimal surface the app needs; tests pass a fake that implements it. */
export interface LiveSocket {
  on(event: string, handler: (payload: never) => void): unknown;
  off(event: string, handler: (payload: never) => void): unknown;
  connect(): unknown;
  disconnect(): unknown;
  readonly connected: boolean;
}

export type SocketFactory = () => LiveSocket;

/** Same-origin Socket.IO (proxied to the backend). WebSocket first, long-polling as a fallback; reconnects forever with backoff; errors surface as status only. */
export const createSocket: SocketFactory = () =>
  io({
    path: "/socket.io",
    autoConnect: false,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 10000,
    transports: ["websocket", "polling"],
    tryAllTransports: true,
  }) as unknown as LiveSocket;
