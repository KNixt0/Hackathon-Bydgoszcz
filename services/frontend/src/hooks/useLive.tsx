import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createSocket, type LiveSocket, type ServerEventName, type ServerEvents, type SocketFactory } from "../api/socket";

export type ConnectionStatus = "connecting" | "online" | "offline";

interface LiveContextValue {
  status: ConnectionStatus;
  socket: LiveSocket | null;
}

const LiveContext = createContext<LiveContextValue>({ status: "offline", socket: null });

/** Owns the single Socket.IO connection. Connection failures only change `status`; nothing is thrown or logged. */
export function LiveProvider({ children, socketFactory = createSocket }: { children: ReactNode; socketFactory?: SocketFactory }) {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [socket, setSocket] = useState<LiveSocket | null>(null);

  useEffect(() => {
    let s: LiveSocket;
    try {
      s = socketFactory();
    } catch {
      setStatus("offline");
      return;
    }
    const onConnect = () => setStatus("online");
    const onDown = () => setStatus("offline");
    s.on("connect", onConnect);
    s.on("disconnect", onDown);
    s.on("connect_error", onDown);
    setSocket(s);
    s.connect();
    return () => {
      s.off("connect", onConnect);
      s.off("disconnect", onDown);
      s.off("connect_error", onDown);
      s.disconnect();
    };
  }, [socketFactory]);

  const value = useMemo(() => ({ status, socket }), [status, socket]);
  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}

export function useConnectionStatus(): ConnectionStatus {
  return useContext(LiveContext).status;
}

/** Subscribes to one server event for the lifetime of the component. The handler may change between renders. */
export function useLiveEvent<E extends ServerEventName>(event: E, handler: (payload: ServerEvents[E]) => void) {
  const { socket } = useContext(LiveContext);
  const ref = useRef(handler);
  useEffect(() => {
    ref.current = handler;
  }, [handler]);
  useEffect(() => {
    if (!socket) return;
    const listener = (payload: ServerEvents[E]) => {
      if (payload && typeof payload === "object") ref.current(payload);
    };
    socket.on(event, listener as (p: never) => void);
    return () => {
      socket.off(event, listener as (p: never) => void);
    };
  }, [socket, event]);
}
