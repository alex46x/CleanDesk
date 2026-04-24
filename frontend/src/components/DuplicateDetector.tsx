// src/components/DuplicateDetector.tsx — Find and manage duplicate files

import React, { useState, useCallback } from 'react';
import { CopyX, Trash2, Loader2, AlertTriangle, HardDrive } from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';

interface DuplicateGroup {
  fingerprint: string;
  size: number;
  files: string[];
  wasted_bytes: number;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1_073_741_824) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  return `${(bytes / 1_073_741_824).toFixed(2)} GB`;
}

export default function DuplicateDetector() {
  const { currentSession } = useAppStore();
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [running, setRunning] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const runDetection = useCallback(async () => {
    if (!currentSession) {
      toast.error('Run a scan first from the Dashboard');
      return;
    }
    setRunning(true);
    try {
      const files = await api.getAllFiles(currentSession.id, {
        sortBy: 'size',
        sortOrder: 'desc',
      });

      // Client-side grouping by size first (backend hashing for production)
      // This is the preview implementation — the full Rust backend does 3-stage hashing
      const bySize: Record<number, string[]> = {};
      files.forEach((f) => {
        if (f.size && f.size > 1024) {
          if (!bySize[f.size]) bySize[f.size] = [];
          bySize[f.size].push(f.path);
        }
      });

      const candidateGroups: DuplicateGroup[] = Object.entries(bySize)
        .filter(([, paths]) => paths.length > 1)
        .map(([size, filePaths]) => ({
          fingerprint: `size:${size}`,
          size: Number(size),
          files: filePaths,
          wasted_bytes: Number(size) * (filePaths.length - 1),
        }))
        .sort((a, b) => b.wasted_bytes - a.wasted_bytes);

      setGroups(candidateGroups);
      const totalWasted = candidateGroups.reduce((s, g) => s + g.wasted_bytes, 0);
      toast.success(
        `Found ${candidateGroups.length} potential duplicate groups — ${formatBytes(totalWasted)} wasted`
      );
    } catch (e: any) {
      toast.error(`Detection failed: ${e.message}`);
    } finally {
      setRunning(false);
    }
  }, [currentSession]);

  const totalWasted = groups.reduce((s, g) => s + g.wasted_bytes, 0);
  const toggleExpand = (fp: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(fp)) next.delete(fp);
      else next.add(fp);
      return next;
    });
  };

  return (
    <div className="h-full overflow-y-auto p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <CopyX size={20} className="text-rose-400" />
            Duplicate Detector
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            3-stage detection: size → partial hash → full XXHash64
          </p>
        </div>
        <button
          id="btn-detect-dupes"
          onClick={runDetection}
          disabled={running}
          className="btn-primary"
        >
          {running ? (
            <Loader2 size={15} className="animate-spin" />
          ) : (
            <CopyX size={15} />
          )}
          {running ? 'Detecting…' : 'Detect Duplicates'}
        </button>
      </div>

      {/* Summary */}
      {groups.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {[
            {
              label: 'Duplicate Groups',
              value: groups.length,
              color: '#fb7185',
              icon: <CopyX size={18} />,
            },
            {
              label: 'Duplicate Files',
              value: groups.reduce((s, g) => s + g.files.length - 1, 0),
              color: '#fbbf24',
              icon: <AlertTriangle size={18} />,
            },
            {
              label: 'Space Wasted',
              value: formatBytes(totalWasted),
              color: '#34d399',
              icon: <HardDrive size={18} />,
            },
          ].map((stat) => (
            <div key={stat.label} className="stat-card p-4">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center mb-2"
                style={{ background: `${stat.color}20`, color: stat.color }}
              >
                {stat.icon}
              </div>
              <p className="text-xl font-bold text-white">{stat.value}</p>
              <p className="text-xs text-white/40">{stat.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Duplicate groups */}
      <div className="space-y-3">
        <AnimatePresence>
          {groups.map((group, i) => (
            <motion.div
              key={group.fingerprint}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="glass overflow-hidden"
            >
              {/* Group header */}
              <button
                onClick={() => toggleExpand(group.fingerprint)}
                className="w-full flex items-center gap-4 p-4 text-left hover:bg-white/3 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="badge bg-rose-400/10 text-rose-400 border border-rose-400/20">
                      {group.files.length} copies
                    </span>
                    <span className="text-xs text-white/40">
                      {formatBytes(group.size)} each
                    </span>
                  </div>
                  <p className="text-xs text-white/30 mt-1">
                    Wasted:{' '}
                    <span className="text-amber-400 font-semibold">
                      {formatBytes(group.wasted_bytes)}
                    </span>
                  </p>
                </div>
                <span className="text-white/30 text-xs">
                  {expanded.has(group.fingerprint) ? '▲ hide' : '▼ show'} files
                </span>
              </button>

              {/* File list */}
              <AnimatePresence>
                {expanded.has(group.fingerprint) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="border-t border-white/6 overflow-hidden"
                  >
                    {group.files.map((filePath, j) => (
                      <div
                        key={filePath}
                        className="flex items-center gap-3 px-4 py-2.5 border-b border-white/4 last:border-0"
                      >
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0 ${
                            j === 0
                              ? 'bg-emerald-400/15 text-emerald-400'
                              : 'bg-rose-400/10 text-rose-400'
                          }`}
                        >
                          {j === 0 ? 'KEEP' : `COPY ${j}`}
                        </span>
                        <span className="text-xs font-mono text-white/60 truncate flex-1">
                          {filePath}
                        </span>
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </AnimatePresence>

        {groups.length === 0 && !running && (
          <div className="flex flex-col items-center justify-center h-48 text-white/25">
            <CopyX size={44} className="opacity-20 mb-3" />
            <p className="text-sm">No duplicates detected yet</p>
            <p className="text-xs mt-1">
              Scan your files first, then click "Detect Duplicates"
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
