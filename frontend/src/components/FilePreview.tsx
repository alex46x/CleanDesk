// src/components/FilePreview.tsx — Browse scanned files and preview before organising

import React, { useDeferredValue, useEffect, useMemo, useState } from 'react';
import {
  Search, ChevronDown, SortAsc, SortDesc,
  Image, Video, Music, FileText, Code, Archive,
  File, ExternalLink, CheckSquare, Loader2,
} from 'lucide-react';
import { useAppStore, FileRecord } from '@/store/appStore';
import { api } from '@/lib/api';

const CATEGORY_COLORS: Record<string, string> = {
  Images: 'text-cyan-400 bg-cyan-400/10',
  Videos: 'text-amber-400 bg-amber-400/10',
  Audio: 'text-violet-400 bg-violet-400/10',
  Documents: 'text-emerald-400 bg-emerald-400/10',
  Code: 'text-rose-400 bg-rose-400/10',
  Archives: 'text-blue-400 bg-blue-400/10',
  Others: 'text-white/50 bg-white/5',
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  Images: <Image size={12} />,
  Videos: <Video size={12} />,
  Audio: <Music size={12} />,
  Documents: <FileText size={12} />,
  Code: <Code size={12} />,
  Archives: <Archive size={12} />,
};

const PAGE_SIZE = 50;

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1_073_741_824) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  return `${(bytes / 1_073_741_824).toFixed(2)} GB`;
}

type SortKey = 'name' | 'size' | 'category' | 'last_modified';

export default function FilePreview() {
  const {
    currentSession,
    categoryStats,
    selectedFiles,
    toggleFileSelection,
    clearSelection,
  } = useAppStore();

  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortAsc, setSortAsc] = useState(true);
  const [page, setPage] = useState(0);
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [totalFiles, setTotalFiles] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search.trim());

  const categories = useMemo(() => {
    const known = Object.keys(categoryStats);
    if (known.length > 0) {
      return ['All', ...known.sort()];
    }

    const fromPage = new Set(files.map((file) => file.category || 'Others'));
    return ['All', ...Array.from(fromPage).sort()];
  }, [categoryStats, files]);

  useEffect(() => {
    setPage(0);
  }, [currentSession?.id, deferredSearch, categoryFilter]);

  useEffect(() => {
    if (!currentSession) {
      setFiles([]);
      setTotalFiles(0);
      setLoadError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setLoadError(null);

    api.getFiles(currentSession.id, {
      category: categoryFilter === 'All' ? undefined : categoryFilter,
      search: deferredSearch || undefined,
      sortBy: sortKey,
      sortOrder: sortAsc ? 'asc' : 'desc',
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    })
      .then((response) => {
        if (cancelled) return;
        setFiles(response.items);
        setTotalFiles(response.total);

        const maxPage = Math.max(0, Math.ceil(response.total / PAGE_SIZE) - 1);
        if (page > maxPage) {
          setPage(maxPage);
        }
      })
      .catch((error: any) => {
        if (cancelled) return;
        setFiles([]);
        setTotalFiles(0);
        setLoadError(error.response?.data?.detail || error.message || 'Failed to load files');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentSession, categoryFilter, deferredSearch, sortKey, sortAsc, page]);

  const totalPages = Math.max(1, Math.ceil(totalFiles / PAGE_SIZE));

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc((value) => !value);
      return;
    }

    setSortKey(key);
    setSortAsc(true);
  };

  const openInExplorer = (path: string) => {
    (window as any).electron?.openFileLocation(path);
  };

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden">
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold text-white">File Preview</h1>
          <p className="text-sm text-white/40 mt-0.5">
            {totalFiles.toLocaleString()} files
            {selectedFiles.size > 0 && (
              <span className="ml-2 text-violet-400">
                ({selectedFiles.size} selected)
              </span>
            )}
          </p>
        </div>
        {selectedFiles.size > 0 && (
          <button
            id="btn-clear-selection"
            onClick={clearSelection}
            className="btn-secondary text-xs"
          >
            Clear selection
          </button>
        )}
      </div>

      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            id="input-file-search"
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search files…"
            className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500"
          />
        </div>

        <div className="relative">
          <select
            id="select-category"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="appearance-none pl-4 pr-8 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500 cursor-pointer"
          >
            {categories.map((category) => (
              <option key={category} value={category} className="bg-[#1a1a24]">
                {category}
              </option>
            ))}
          </select>
          <ChevronDown size={12} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 pointer-events-none" />
        </div>
      </div>

      <div className="flex items-center gap-4 px-4 py-2 text-xs text-white/30 font-medium flex-shrink-0">
        <div className="w-6 flex-shrink-0" />
        <button
          className="flex-1 text-left flex items-center gap-1 hover:text-white/60 transition-colors"
          onClick={() => toggleSort('name')}
        >
          Name {sortKey === 'name' ? (sortAsc ? <SortAsc size={11} /> : <SortDesc size={11} />) : null}
        </button>
        <button
          className="w-24 text-left flex items-center gap-1 hover:text-white/60 transition-colors"
          onClick={() => toggleSort('category')}
        >
          Category {sortKey === 'category' ? (sortAsc ? <SortAsc size={11} /> : <SortDesc size={11} />) : null}
        </button>
        <button
          className="w-20 text-right flex items-center justify-end gap-1 hover:text-white/60 transition-colors"
          onClick={() => toggleSort('size')}
        >
          Size {sortKey === 'size' ? (sortAsc ? <SortAsc size={11} /> : <SortDesc size={11} />) : null}
        </button>
        <div className="w-8 flex-shrink-0" />
      </div>

      <div className="flex-1 overflow-y-auto space-y-0.5">
        {loading && (
          <div className="flex items-center justify-center h-24 text-white/40 gap-2">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Loading files…</span>
          </div>
        )}

        {!loading && files.map((file) => (
          <div key={file.id} className="table-row">
            <button
              onClick={() => toggleFileSelection(file.id)}
              className={`w-6 h-6 flex-shrink-0 rounded-md border transition-colors ${
                selectedFiles.has(file.id)
                  ? 'bg-violet-600 border-violet-500'
                  : 'bg-transparent border-white/15 hover:border-violet-500'
              }`}
            >
              {selectedFiles.has(file.id) && (
                <CheckSquare size={12} className="text-white m-auto" />
              )}
            </button>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{file.name}</p>
              <p className="text-xs text-white/30 truncate font-mono">{file.path}</p>
            </div>

            <div className="w-24">
              <span className={`badge text-[10px] ${CATEGORY_COLORS[file.category || 'Others']}`}>
                {CATEGORY_ICONS[file.category || 'Others'] || <File size={10} />}
                {file.category || 'Others'}
              </span>
            </div>

            <div className="w-20 text-right text-xs text-white/50 font-mono">
              {formatBytes(file.size)}
            </div>

            <button
              onClick={() => openInExplorer(file.path)}
              className="w-8 flex-shrink-0 text-white/25 hover:text-cyan-400 transition-colors"
            >
              <ExternalLink size={13} />
            </button>
          </div>
        ))}

        {!loading && files.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 text-white/25">
            <File size={40} className="mb-2 opacity-30" />
            <p className="text-sm">{loadError || 'No files found'}</p>
            <p className="text-xs mt-1">
              {currentSession ? 'Try a different search or category filter' : 'Run a scan from the Dashboard'}
            </p>
          </div>
        )}
      </div>

      {totalFiles > PAGE_SIZE && (
        <div className="flex items-center justify-center gap-2 flex-shrink-0 pt-2">
          <button
            disabled={page === 0 || loading}
            onClick={() => setPage((value) => value - 1)}
            className="btn-secondary text-xs disabled:opacity-30"
          >
            Prev
          </button>
          <span className="text-xs text-white/40">
            Page {page + 1} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages - 1 || loading}
            onClick={() => setPage((value) => value + 1)}
            className="btn-secondary text-xs disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
