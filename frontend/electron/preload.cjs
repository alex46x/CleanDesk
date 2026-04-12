/**
 * electron/preload.js — Secure IPC bridge exposed to the renderer.
 * Only explicitly listed APIs are accessible from React.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  getPlatform: () => ipcRenderer.invoke('get-platform'),
  openFileLocation: (filePath) => ipcRenderer.invoke('open-file-location', filePath),
  minimize: () => ipcRenderer.invoke('minimize-window'),
  maximize: () => ipcRenderer.invoke('maximize-window'),
  close: () => ipcRenderer.invoke('close-window'),
});
