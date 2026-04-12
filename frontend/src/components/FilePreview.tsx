// src/components/FilePreview.tsx — Browse scanned files and preview before organising

import React, { useState, useEffect, useMemo } from 'react';
import {
  Search, ChevronDown, SortAsc, SortDesc,
  Image, Video, Music, FileText, Code, Archive,
  File, ExternalLink, CheckSquare,
} from 'lucide-react';
import { useAppStore, FileRecord } from '@/store/appStore';
import { motion, AnimatePresence } from 'framer-motion';

const CATEGORY_COLORS: Record<string, string> = {
  Images:      'text-cyan-400 bg-cyan-400/10',
  Videos:      'text-amber-400 bg-amber-400/10',
  Audio:       'text-violet-400 bg-violet-400/10',
  Documents:   'text-emerald-400 bg-emerald-400/10',
  Code:        'text-rose-400 bg-rose-400/10',
  Archives:    'text-blue-400 bg-blue-400/10',
  Others:      'text-white/50 bg-white/5',
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  Images:    <Image size={12} />,
  Videos:    <Video size={12} />,
  Audio:     <Music size={12} />,
  Documents: <FileText size={12} />,
  Code:      <Code size={12} />,
  Archives:  <Archive size={12} />,
};

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1_073_741_824) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  return `${(bytes / 1_073_741_824).toFixed(2)} GB`;
}

type SortKey = 'name' | 'size' | 'category' | 'last_modified';

export default function FilePreview() {
  const { files, selectedFiles, toggleFileSelection, clearSelection } = useAppStore();
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortAsc, setSortAsc] = useState(true);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  const categories = useMemo(() => {
    const cats = new Set(files.map((f) => f.category || 'Others'));
    return ['All', ...Array.from(cats).sort()];
  }, [files]);

  const filtered = useMemo(() => {
    let arr = files;
    if (categoryFilter !== 'All') arr = arr.filter((f) => f.category === categoryFilter);
    if (search) {
      const q = search.toLowerCase();
      arr = arr.filter((f) => f.name.toLowerCase().includes(q) || f.path.toLowerCase().includes(q));
    }
    arr = [...arr].sort((a, b) => {
      const va = a[sortKey] ?? '';
      const vb = b[sortKey] ?? '';
      const cmp = String(va).localeCompare(String(vb), undefined, { numeric: true });
      return sortAsc ? cmp : -cmp;
    });
    return arr;
  }, [files, categoryFilter, search, sortKey, sortAsc]);

  const paginated = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc((a) => !a);
    else { setSortKey(key); setSortAsc(true); }
  };

  const openInExplorer = (path: string) => {
    (window as any).electron?.openFileLocation(path);
  };

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold text-white">File Preview</h1>
          <p className="text-sm text-white/40 mt-0.5">
            {filtered.length.toLocaleString()} files
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

      {/* Filters */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {/* Search */}
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            id="input-file-search"
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder="Search files…"
            className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500"
          />
        </div>

        {/* Category filter */}
        <div className="relative">
          <select
            id="select-category"
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setPage(0); }}
            className="appearance-none pl-4 pr-8 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500 cursor-pointer"
          >
            {categories.map((c) => (
              <option key={c} value={c} className="bg-[#1a1a24]">{c}</option>
            ))}
          </select>
          <ChevronDown size={12} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 pointer-events-none" />
        </div>
      </div>

      {/* Table header */}
      <div className="flex items-center gap-4 px-4 py-2 text-xs text-white/30 font-medium flex-shrink-0">
        <div className="w-6 flex-shrink-0" />
        <button
          className="flex-1 text-left flex items-center gap-1 hover:text-white/60 transition-colors"
          onClick={() => toggleSort('name')}
        >
          Name {sortKey === 'name' ? (sortAsc ? <SortAsc size={11}/> : <SortDesc size={11}/>) : null}
        </button>
        <button
          className="w-24 text-left flex items-center gap-1 hover:text-white/60 transition-colors"
          onClick={() => toggleSort('category')}
        >
          Category {sortKey === 'category' ? (sortAsc ? <SortAsc size={11}/> : <SortDesc size={11}/>) : null}
        </button>
        <button
          className="w-20 text-right flex items-center justify-end gap-1 hover:text-white/60 transition-colors"
          onClick={() => toggleSort('size')}
        >
          Size {sortKey === 'size' ? (sortAsc ? <SortAsc size={11}/> : <SortDesc size={11}/>) : null}
        </button>
        <div className="w-8 flex-shrink-0" />
      </div>

      {/* Table body */}
      <div className="flex-1 overflow-y-auto space-y-0.5">
        <AnimatePresence mode="popLayout">
          {paginated.map((file, i) => (
            <motion.div
              key={file.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ delay: i * 0.01 }}
              className="table-row"
            >
              {/* Checkbox */}
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

              {/* Name + path */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{file.name}</p>
                <p className="text-xs text-white/30 truncate font-mono">{file.path}</p>
              </div>

              {/* Category badge */}
              <div className="w-24">
                <span
                  className={`badge text-[10px] ${
                    CATEGORY_COLORS[file.category || 'Others']
                  }`}
                >
                  {CATEGORY_ICONS[file.category || 'Others'] || <File size={10} />}
                  {file.category || 'Others'}
                </span>
              </div>

              {/* Size */}
              <div className="w-20 text-right text-xs text-white/50 font-mono">
                {formatBytes(file.size)}
              </div>

              {/* Open in explorer */}
              <button
                onClick={() => openInExplorer(file.path)}
                className="w-8 flex-shrink-0 text-white/25 hover:text-cyan-400 transition-colors"
              >
                <ExternalLink size={13} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>

        {paginated.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 text-white/25">
            <File size={40} className="mb-2 opacity-30" />
            <p className="text-sm">No files found</p>
            <p className="text-xs mt-1">Run a scan from the Dashboard</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 flex-shrink-0 pt-2">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            className="btn-secondary text-xs disabled:opacity-30"
          >
            Prev
          </button>
          <span className="text-xs text-white/40">
            Page {page + 1} / {totalPages}
          </span>
          <button
            disabled={page === totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
            className="btn-secondary text-xs disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
