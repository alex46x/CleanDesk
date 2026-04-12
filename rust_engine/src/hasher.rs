// rust_engine/src/hasher.rs — Parallel XXHash64 file hashing
//
// Algorithm:
//   1. Read file in 8 MB chunks (avoids large memory usage on huge files)
//   2. Feed chunks to XxHash64 hasher
//   3. Return hex string digest
//
// All files are hashed concurrently via rayon thread pool.

use anyhow::Result;
use rayon::prelude::*;
use std::collections::HashMap;
use std::fs::File;
use std::hash::Hasher;
use std::io::{BufReader, Read};
use twox_hash::XxHash64;

const CHUNK_SIZE: usize = 8 * 1024 * 1024;   // 8 MB
const SEED: u64 = 0;

/// Hash a single file with XXHash64.
/// Returns None if the file cannot be read.
pub fn hash_file(path: &str) -> Option<String> {
    let file = File::open(path).ok()?;
    let mut reader = BufReader::with_capacity(CHUNK_SIZE, file);
    let mut hasher = XxHash64::with_seed(SEED);
    let mut buf = vec![0u8; CHUNK_SIZE];

    loop {
        match reader.read(&mut buf) {
            Ok(0) => break,
            Ok(n) => hasher.write(&buf[..n]),
            Err(_) => return None,
        }
    }

    Some(format!("{:016x}", hasher.finish()))
}

/// Hash a slice of file paths in parallel.
/// Returns a HashMap from path → hex digest.
/// Files that cannot be read will have an empty string value.
pub fn hash_files_parallel(paths: &[String]) -> Result<HashMap<String, String>> {
    let results: HashMap<String, String> = paths
        .par_iter()
        .map(|path| {
            let digest = hash_file(path).unwrap_or_default();
            (path.clone(), digest)
        })
        .collect();

    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_hash_consistency() {
        let mut f1 = NamedTempFile::new().unwrap();
        let mut f2 = NamedTempFile::new().unwrap();
        let content = b"hello smart file organizer";
        f1.write_all(content).unwrap();
        f2.write_all(content).unwrap();

        let h1 = hash_file(f1.path().to_str().unwrap()).unwrap();
        let h2 = hash_file(f2.path().to_str().unwrap()).unwrap();
        assert_eq!(h1, h2, "Same content must produce same hash");
        assert_eq!(h1.len(), 16, "XXHash64 hex should be 16 chars");
    }

    #[test]
    fn test_different_content_different_hash() {
        let mut f1 = NamedTempFile::new().unwrap();
        let mut f2 = NamedTempFile::new().unwrap();
        f1.write_all(b"file one content").unwrap();
        f2.write_all(b"file two content").unwrap();

        let h1 = hash_file(f1.path().to_str().unwrap()).unwrap();
        let h2 = hash_file(f2.path().to_str().unwrap()).unwrap();
        assert_ne!(h1, h2);
    }
}
