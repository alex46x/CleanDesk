// src/components/LogViewer.tsx — Activity log with undo support

import React, { useEffect, useState, useCallback } from 'react';
import {
  ScrollText, RotateCcw, CheckCircle, XCircle,
  MinusCircle, RefreshCw, Filter,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAppStore } from '@/store/appStore';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

interface Log {
  id: number;
  old_path: string;
  new_path: string;
  operation: string;
  status: string;
  timestamp: number;
  error_message: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  success: 'text-emerald-400 bg-emerald-400/10',
  failed:  'text-rose-400 bg-rose-400/10',
  undone:  'text-amber-400 bg-amber-400/10',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  success: <CheckCircle size={12} />,
  failed:  <XCircle size={12} />,
  undone:  <MinusCircle size={12} />,
};

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

export default function LogViewer() {
  const { logs, setLogs } = useAppStore();
  const [statusFilter, setStatusFilter] = useState('all');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const [undoing, setUndoing] = useState(false);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getLogs(statusFilter === 'all' ? undefined : statusFilter);
      setLogs(data);
    } catch {
      toast.error('Failed to load logs');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, setLogs]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleUndo = async () => {
    if (selected.size === 0) {
      toast.error('Select at least one log entry to undo');
      return;
    }
    setUndoing(true);
    try {
      const result = await api.undoMoves(Array.from(selected));
      toast.success(`Undone: ${result.succeeded} / ${result.total} moves reversed`);
      setSelected(new Set());
      await fetchLogs();
    } catch (e: any) {
      toast.error(`Undo failed: ${e.message}`);
    } finally {
      setUndoing(false);
    }
  };

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ScrollText size={20} className="text-violet-400" />
            Activity Log
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            {logs.length} entries — select entries to undo
          </p>
        </div>
        <div className="flex items-center gap-3">
          {selected.size > 0 && (
            <button
              id="btn-undo"
              onClick={handleUndo}
              disabled={undoing}
              className="btn-secondary text-amber-400 border-amber-400/30 hover:bg-amber-400/10"
            >
              <RotateCcw size={14} className={undoing ? 'animate-spin' : ''} />
              Undo {selected.size} move{selected.size > 1 ? 's' : ''}
            </button>
          )}
          <button
            id="btn-refresh-logs"
            onClick={fetchLogs}
            disabled={loading}
            className="btn-secondary"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Status filter tabs */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Filter size={13} className="text-white/30" />
        {['all', 'success', 'failed', 'undone'].map((s) => (
          <button
            key={s}
            id={`filter-${s}`}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
              statusFilter === s
                ? 'bg-violet-600/30 text-violet-300 border border-violet-500/30'
                : 'text-white/40 hover:text-white hover:bg-white/5'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Log entries */}
      <div className="flex-1 overflow-y-auto space-y-1.5">
        <AnimatePresence>
          {logs.map((log) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              onClick={() => log.status === 'success' && toggleSelect(log.id)}
              className={`flex items-start gap-3 px-4 py-3 rounded-xl border transition-all cursor-default ${
                selected.has(log.id)
                  ? 'bg-amber-400/8 border-amber-400/20'
                  : 'bg-white/3 border-white/6 hover:bg-white/5'
              } ${log.status === 'success' ? 'cursor-pointer' : ''}`}
            >
              {/* Checkbox */}
              {log.status === 'success' && (
                <div
                  className={`w-4 h-4 rounded border flex-shrink-0 mt-0.5 transition-colors ${
                    selected.has(log.id)
                      ? 'bg-amber-400 border-amber-400'
                      : 'bg-transparent border-white/20'
                  }`}
                />
              )}

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`badge text-[10px] ${STATUS_STYLES[log.status] || STATUS_STYLES.failed}`}>
                    {STATUS_ICONS[log.status]}
                    {log.status}
                  </span>
                  <span className="text-[10px] text-white/30 font-mono uppercase">{log.operation}</span>
                  <span className="text-[10px] text-white/25 ml-auto">{formatTime(log.timestamp)}</span>
                </div>
                <p className="text-xs font-mono text-white/60 truncate">
                  <span className="text-white/30">from: </span>{log.old_path}
                </p>
                <p className="text-xs font-mono text-white/80 truncate">
                  <span className="text-white/30">  to: </span>{log.new_path}
                </p>
                {log.error_message && (
                  <p className="text-xs text-rose-400 mt-1 truncate">⚠ {log.error_message}</p>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {logs.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-48 text-white/25">
            <ScrollText size={40} className="opacity-30 mb-2" />
            <p className="text-sm">No log entries yet</p>
            <p className="text-xs mt-1">File operations will appear here</p>
          </div>
        )}
      </div>
    </div>
  );
}
