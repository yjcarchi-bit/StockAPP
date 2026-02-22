/**
 * 实时数据 Hook
 * =============
 * 提供实时行情和策略信号的 WebSocket 连接管理
 *
 * 特性:
 * - 自动重连机制
 * - 心跳检测
 * - 数据缓存
 * - 连接状态管理
 */

import { useEffect, useState, useCallback, useRef } from 'react';

export interface RealtimeQuote {
  code: string;
  name: string;
  price: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  amount: number;
  change: number;
  change_pct: number;
  timestamp: string;
}

export interface StrategySignal {
  action: 'buy' | 'sell' | 'defensive';
  target_etf: string;
  target_name: string;
  score: number;
  reason: string;
  timestamp: string;
  all_scores: Array<{
    code: string;
    name: string;
    score: number;
    annualized_return: number;
    r_squared: number;
  }>;
}

export interface ConnectionStatus {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  reconnectCount: number;
  lastHeartbeat: string | null;
}

export interface UseRealtimeDataOptions {
  wsUrl?: string;
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

export interface UseRealtimeDataReturn {
  quotes: Map<string, RealtimeQuote>;
  signal: StrategySignal | null;
  status: ConnectionStatus;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
}

const DEFAULT_WS_URL = `ws://${window.location.hostname}:8000/ws/realtime`;
const DEFAULT_RECONNECT_INTERVAL = 3000;
const DEFAULT_MAX_RECONNECT_ATTEMPTS = 10;
const DEFAULT_HEARTBEAT_INTERVAL = 30000;

export function useRealtimeData(
  options: UseRealtimeDataOptions = {}
): UseRealtimeDataReturn {
  const {
    wsUrl = DEFAULT_WS_URL,
    autoConnect = true,
    reconnectInterval = DEFAULT_RECONNECT_INTERVAL,
    maxReconnectAttempts = DEFAULT_MAX_RECONNECT_ATTEMPTS,
    heartbeatInterval = DEFAULT_HEARTBEAT_INTERVAL,
  } = options;

  const [quotes, setQuotes] = useState<Map<string, RealtimeQuote>>(new Map());
  const [signal, setSignal] = useState<StrategySignal | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>({
    connected: false,
    connecting: false,
    error: null,
    reconnectCount: 0,
    lastHeartbeat: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountRef = useRef(0);

  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }

    heartbeatTimeoutRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'heartbeat' }));
        startHeartbeat();
      }
    }, heartbeatInterval);
  }, [heartbeatInterval]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus((prev) => ({ ...prev, connecting: true, error: null }));

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus({
          connected: true,
          connecting: false,
          error: null,
          reconnectCount: reconnectCountRef.current,
          lastHeartbeat: new Date().toISOString(),
        });
        reconnectCountRef.current = 0;
        startHeartbeat();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'all_quotes':
              if (data.data) {
                const newQuotes = new Map<string, RealtimeQuote>();
                Object.entries(data.data).forEach(([code, quote]) => {
                  newQuotes.set(code, quote as RealtimeQuote);
                });
                setQuotes(newQuotes);
              }
              break;

            case 'realtime_quote':
              if (data.data) {
                setQuotes((prev) => {
                  const newQuotes = new Map(prev);
                  newQuotes.set(data.data.code, data.data);
                  return newQuotes;
                });
              }
              break;

            case 'strategy_signal':
              if (data.data) {
                setSignal(data.data);
              }
              break;

            case 'heartbeat':
              setStatus((prev) => ({
                ...prev,
                lastHeartbeat: new Date().toISOString(),
              }));
              break;

            case 'status':
              break;

            case 'error':
              setStatus((prev) => ({
                ...prev,
                error: data.message || '未知错误',
              }));
              break;
          }
        } catch (e) {
          console.error('解析消息失败:', e);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
        setStatus((prev) => ({
          ...prev,
          connecting: false,
          error: '连接错误',
        }));
      };

      ws.onclose = (event) => {
        clearTimers();
        setStatus((prev) => ({
          ...prev,
          connected: false,
          connecting: false,
        }));

        if (
          !event.wasClean &&
          reconnectCountRef.current < maxReconnectAttempts
        ) {
          reconnectCountRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else if (reconnectCountRef.current >= maxReconnectAttempts) {
          setStatus((prev) => ({
            ...prev,
            error: '重连次数超限',
          }));
        }
      };
    } catch (error) {
      setStatus((prev) => ({
        ...prev,
        connecting: false,
        error: '创建连接失败',
      }));
    }
  }, [wsUrl, maxReconnectAttempts, reconnectInterval, startHeartbeat, clearTimers]);

  const disconnect = useCallback(() => {
    clearTimers();
    reconnectCountRef.current = 0;

    if (wsRef.current) {
      wsRef.current.close(1000, '用户断开');
      wsRef.current = null;
    }

    setStatus({
      connected: false,
      connecting: false,
      error: null,
      reconnectCount: 0,
      lastHeartbeat: null,
    });
  }, [clearTimers]);

  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(connect, 100);
  }, [disconnect, connect]);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    quotes,
    signal,
    status,
    connect,
    disconnect,
    reconnect,
  };
}

export function useRealtimeQuotes(
  options: UseRealtimeDataOptions = {}
): {
  quotes: RealtimeQuote[];
  status: ConnectionStatus;
  connect: () => void;
  disconnect: () => void;
} {
  const { quotes: quoteMap, status, connect, disconnect } = useRealtimeData(options);

  const quotes = Array.from(quoteMap.values()).sort((a, b) => {
    if (a.change_pct !== b.change_pct) {
      return b.change_pct - a.change_pct;
    }
    return a.code.localeCompare(b.code);
  });

  return { quotes, status, connect, disconnect };
}

export function useStrategySignal(
  options: UseRealtimeDataOptions = {}
): {
  signal: StrategySignal | null;
  status: ConnectionStatus;
  connect: () => void;
  disconnect: () => void;
} {
  const { signal, status, connect, disconnect } = useRealtimeData(options);

  return { signal, status, connect, disconnect };
}
