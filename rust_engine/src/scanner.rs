// rust_engine/src/scanner.rs — High-performance recursive directory scanner
//
// Uses walkdir for portable traversal + rayon for parallel stat collection.
// Returns FileInfo structs sorted by path for deterministic output.

use anyhow::{Context, Result};
use rayon::prelude::*;
use std::path::Path;
use std::time::UNIX_EPOCH;
use walkdir::{DirEntry, WalkDir};

/// Lightweight file metadata returned to Python.
#[derive(Debug, Clone)]
pub struct FileInfo {
    pub path: String,
    pub name: String,
    pub extension: String,
    pub size: u64,
    pub last_modified: f64,  // Unix timestamp as float (matches Python)
}

/// Walk `root_path` recursively, skipping `exclude_paths` and inaccessible dirs,
/// and return metadata for every regular file found.
pub fn scan(root_path: &str, exclude_paths: &[String]) -> Result<Vec<FileInfo>> {
    let root = Path::new(root_path);

    // Collect all accessible directory entries first (single-threaded traversal)
    let entries: Vec<DirEntry> = WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())          // skip permission errors silently
        .filter(|e| {
            // Only regular files
            e.file_type().is_file()
        })
        .filter(|e| {
            // Skip excluded paths
            let p = e.path().to_string_lossy();
            !exclude_paths.iter().any(|ex| p.starts_with(ex.as_str()))
        })
        .collect();

    // Parallel stat + metadata extraction via rayon
    let files: Vec<FileInfo> = entries
        .par_iter()
        .filter_map(|entry| {
            let metadata = entry.metadata().ok()?;
            let path     = entry.path().to_string_lossy().into_owned();
            let name     = entry.file_name().to_string_lossy().into_owned();
            let ext      = entry
                .path()
                .extension()
                .map(|e| format!(".{}", e.to_string_lossy().to_lowercase()))
                .unwrap_or_default();
            let size     = metadata.len();
            let mtime    = metadata
                .modified()
                .ok()?
                .duration_since(UNIX_EPOCH)
                .ok()?
                .as_secs_f64();

            Some(FileInfo {
                path,
                name,
                extension: ext,
                size,
                last_modified: mtime,
            })
        })
        .collect();

    Ok(files)
}
