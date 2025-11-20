/**
 * WebSocket Hook
 * Real-time güncellemeler için custom React hook
 */
import { useEffect, useRef, useState } from 'react';

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

type MessageHandler = (message: WebSocketMessage) => void;

export function useWebSocket(path: string, onMessage?: MessageHandler) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number>();
  const heartbeatIntervalRef = useRef<number>();

  useEffect(() => {
    let isMounted = true;

    const connect = () => {
      if (!isMounted) return;

      const ws = new WebSocket(`${WS_BASE_URL}${path}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected:', path);
        setIsConnected(true);

        // Heartbeat başlat (her 30 saniyede ping)
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        if (event.data === 'pong') return; // Heartbeat response

        try {
          const message = JSON.parse(event.data);
          onMessage?.(message);
        } catch (error) {
          console.error('WebSocket message parse error:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket closed:', path);
        setIsConnected(false);

        // Heartbeat durdur
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
        }

        // 3 saniye sonra yeniden bağlan
        if (isMounted) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        }
      };
    };

    connect();

    return () => {
      isMounted = false;

      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [path]);

  return { isConnected };
}

export default useWebSocket;
