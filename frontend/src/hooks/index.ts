import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { APIRecord, APIListResponse, AnalyticsSummary, ScanRecord, ScanEvent } from "@/types";
import { useState, useEffect, useCallback, useRef } from "react";

// ── Query Keys ───────────────────────────────────────────────────
export const API_KEYS = {
  all:          ()                   => ["apis"]                     as const,
  list:         (filters:  object)   => ["apis", "list", filters]    as const,
  detail:       (id: string)         => ["apis", "detail", id]       as const,
  metrics:      (id: string)         => ["apis", "metrics", id]      as const,
  audit:        (id: string)         => ["apis", "audit", id]        as const,
  analytics:    ()                   => ["analytics", "summary"]     as const,
  decommission: (id: string)         => ["decommission", id]         as const,
};

// ── Analytics ─────────────────────────────────────────────────────
export function useAnalyticsSummary() {
  return useQuery({
    queryKey: API_KEYS.analytics(),
    queryFn: async () => {
      const { data } = await apiClient.get<AnalyticsSummary>("/analytics/summary");
      return data;
    },
    refetchInterval: 30_000, 
  });
}

// ── Fetch API List ────────────────────────────────────────────────
export function useAPIList(filters: {
  status?:    string;
  risk?:      string;
  search?:    string;
  owner?:     string;
  source?:    string;
  sort_by?:   string;
  page?:      number;
  page_size?: number;
} = {}) {
  return useQuery({
    queryKey:  API_KEYS.list(filters),
    queryFn:   async () => {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([k, v]) => v && params.set(k, String(v)));
      const { data } = await apiClient.get<APIListResponse>(`/apis?${params}`);
      return data;
    },
    staleTime:    10_000,
  });
}

// ── Fetch Single API ──────────────────────────────────────────────
export function useAPI(id: string) {
  return useQuery({
    queryKey: API_KEYS.detail(id),
    queryFn:  async () => {
      const { data } = await apiClient.get<APIRecord>(`/apis/${id}`);
      return data;
    },
    enabled:  !!id,
    staleTime: 5_000,
  });
}

// ── Reanalyze API ─────────────────────────────────────────────────
export function useReanalyzeAPI() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post<APIRecord>(`/apis/${id}/reanalyze`);
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(API_KEYS.detail(data.id), data);
      qc.invalidateQueries({ queryKey: API_KEYS.all() });
      qc.invalidateQueries({ queryKey: API_KEYS.analytics() });
    },
  });
}

// ── Decommission ──────────────────────────────────────────────────
export function useStartDecommission() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: async (id: string) => {
        const { data } = await apiClient.post(`/decommission/${id}/start`);
        return data;
      },
      onSuccess: (_, id) => {
        qc.invalidateQueries({ queryKey: API_KEYS.decommission(id) });
      },
    });
}

export function useDecommissionStatus(id: string) {
    return useQuery({
        queryKey: API_KEYS.decommission(id),
        queryFn: async () => {
            const { data } = await apiClient.get(`/decommission/${id}`);
            return data;
        },
        enabled: !!id,
        refetchInterval: (query) => {
           if (query.state.data && (query.state.data as { status?: string }).status !== 'completed') {
               return 1500;
           }
           return false;
        }
    })
}


// ── SSE Hook for Scan ─────────────────────────────────────────────
export function useScan() {
  const [scanId,    setScanId]    = useState<string | null>(null);
  const [status,    setStatus]    = useState<"idle" | "running" | "completed" | "error">("idle");
  const [progress,  setProgress]  = useState(0);
  const [events,    setEvents]    = useState<ScanEvent[]>([]);
  const [apisFound, setApisFound] = useState(0);
  const esRef = useRef<EventSource | null>(null);
  const qc = useQueryClient();

  const startScan = useCallback(async (targets: string[] = ["api_gateway", "github", "k8s", "lambda"]) => {
    setEvents([]);
    setProgress(0);
    setApisFound(0);
    setStatus("running");

    try {
        const { data } = await apiClient.post<{ scan_id: string }>("/scan/start", { targets });
        setScanId(data.scan_id);
    } catch {
        setStatus("error");
    }
  }, []);

  useEffect(() => {
    if (!scanId || status !== "running") return;

    esRef.current?.close();

    // With proxy, we can just use relative path in EventSource or absolute since we run on same host in dev
    // Vite proxy doesn't always proxy EventSource natively if not same-origin, 
    // but relative path "/scan" will hit proxy.
    const es = new EventSource(`/scan/${scanId}/stream`);
    esRef.current = es;

    es.onmessage = (e: MessageEvent) => {
      try {
          const scan: ScanRecord = JSON.parse(e.data);
          setProgress(scan.progress);
          setApisFound(scan.apis_found);
          setEvents(scan.events ?? []);

          if (scan.status === "completed") {
            setStatus("completed");
            es.close();
            // Refresh API list globally when a scan finishes
            qc.invalidateQueries({ queryKey: API_KEYS.all() });
            qc.invalidateQueries({ queryKey: API_KEYS.analytics() });
          }
      } catch (err) {
          console.error("SSE Parse Error", err);
      }
    };

    es.onerror = () => {
        setStatus("error");
    };

    return () => { es.close(); };
  }, [scanId, status, qc]);

  return { startScan, status, progress, events, apisFound, scanId };
}


// ── WebSocket Hook ────────────────────────────────────────────────
import type { WSMessage } from "@/types";

type MessageHandler = (msg: WSMessage) => void;

export function useWebSocket(onMessage: MessageHandler) {
  const wsRef       = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handlerRef  = useRef(onMessage);
  
  useEffect(() => {
      handlerRef.current = onMessage;
  }, [onMessage])

  const connect = useCallback(function connectFn() {
    wsRef.current?.close();

    // Dynamically build WS URL based on current host (proxy doesn't always work securely for ws)
    // We'll use the precise vite config target
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // If not in dev proxy, default to 8000
    const port = window.location.port ? `:${window.location.port}` : "";
    
    // With vite proxy configured with ws: true, we can try same host.
    const ws = new WebSocket(`${protocol}//${window.location.hostname}${port}/ws/monitor`);
    wsRef.current = ws;

    ws.onopen    = ()    => { setConnected(true); console.log("[WS] Connected"); };
    ws.onclose   = ()    => {
      setConnected(false);
      reconnTimer.current = setTimeout(connectFn, 3000);
    };
    ws.onerror   = ()    => ws.close();
    ws.onmessage = (e)   => {
      try {
        const msg: WSMessage = JSON.parse(e.data);
        handlerRef.current(msg);
      } catch { /* ignore parse errors */ }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnTimer.current) clearTimeout(reconnTimer.current);
    };
  }, [connect]);

  return { connected };
}
