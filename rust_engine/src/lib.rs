// rust_engine/src/lib.rs — PyO3 module entry point
//
// Exposes two Python-callable functions:
//   smart_organizer_engine.scan_directory(path, exclude_protected) -> list[dict]
//   smart_organizer_engine.hash_files(paths)                       -> dict[str, str]

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;

mod scanner;
mod hasher;

/// Recursively scan a directory and return file metadata.
///
/// Each item in the returned list is a dict with keys:
///   path, name, extension, size, last_modified
///
/// Protected system paths are automatically excluded.
#[pyfunction]
#[pyo3(signature = (root_path, exclude_paths=None))]
fn scan_directory(
    root_path: String,
    exclude_paths: Option<Vec<String>>,
) -> PyResult<Vec<pyo3::PyObject>> {
    let excludes = exclude_paths.unwrap_or_default();
    let files = scanner::scan(&root_path, &excludes)
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

    Python::with_gil(|py| {
        let result: Vec<pyo3::PyObject> = files
            .into_iter()
            .map(|fi| {
                let dict = pyo3::types::PyDict::new(py);
                dict.set_item("path", &fi.path).unwrap();
                dict.set_item("name", &fi.name).unwrap();
                dict.set_item("extension", &fi.extension).unwrap();
                dict.set_item("size", fi.size).unwrap();
                dict.set_item("last_modified", fi.last_modified).unwrap();
                dict.into()
            })
            .collect();
        Ok(result)
    })
}

/// Compute XXHash64 digests for a list of file paths in parallel.
///
/// Returns a dict mapping path → hex digest (or empty string on error).
#[pyfunction]
fn hash_files(paths: Vec<String>) -> PyResult<std::collections::HashMap<String, String>> {
    let results = hasher::hash_files_parallel(&paths)
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    Ok(results)
}

/// Register the Python module.
#[pymodule]
fn smart_organizer_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_directory, m)?)?;
    m.add_function(wrap_pyfunction!(hash_files, m)?)?;
    m.add("__version__", "0.1.0")?;
    Ok(())
}
