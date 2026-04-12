// src/hooks/useWebSocket.ts — WebSocket hook for real-time progress

import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '@/store/appStore';

const WS_URL = 'ws://localhost:8765/api/scan/ws/progress';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const { setScanProgress, setIsScanning, setCurrentSession } = useAppStore();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => console.log('[WS] Connected');

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);

        if (data.event === 'scan_progress') {
          setScanProgress({
            total_files: data.total_files,
            processed: data.processed,
            files_per_second: data.files_per_second ?? 0,
          });
        }

        if (data.event === 'scan_done' || data.event === 'done') {
          setIsScanning(false);
        }

        if (data.event === 'heartbeat') {
          // ignore — keeps connection alive
        }
      } catch {
        // non-JSON message
      }
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected — reconnecting in 3s');
      setTimeout(connect, 3000);
    };

    ws.onerror = (err) => {
      console.error('[WS] Error', err);
      ws.close();
    };
  }, [setScanProgress, setIsScanning]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { ws: wsRef.current };
}
