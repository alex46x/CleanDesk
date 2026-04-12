/**
 * electron/main.js — Electron main process.
 *
 * Responsibilities:
 *  - Create the BrowserWindow
 *  - Launch the Python FastAPI backend as a child process
 *  - Expose IPC bridge to renderer
 *  - Handle app lifecycle (quit, ready)
 */

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const isDev = process.env.NODE_ENV !== 'production';

let mainWindow = null;
let backendProcess = null;

// ---------------------------------------------------------------------------
// Backend launcher
// ---------------------------------------------------------------------------
function startBackend() {
  const backendCmd = isDev
    ? path.join(__dirname, '..', '..', '.venv', 'Scripts', 'python.exe')
    : path.join(process.resourcesPath, 'backend', 'smart_organizer.exe');

  const backendArgs = isDev
    ? ['-m', 'backend.main']
    : [];

  const cwd = isDev
    ? path.join(__dirname, '..', '..') // repo root
    : process.resourcesPath;

  backendProcess = spawn(backendCmd, backendArgs, {
    cwd,
    shell: false,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });

  backendProcess.stdout.on('data', (d) =>
    console.log('[backend]', d.toString().trim())
  );
  backendProcess.stderr.on('data', (d) =>
    console.error('[backend-err]', d.toString().trim())
  );
  backendProcess.on('close', (code) =>
    console.log('[backend] exited with code', code)
  );
}

// ---------------------------------------------------------------------------
// Window creation
// ---------------------------------------------------------------------------
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0f0f13',
    frame: false,         // Custom title bar in React
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    icon: path.join(__dirname, '..', 'public', 'icon.png'),
  });

  if (isDev) {
    // Wait for Vite dev server
    setTimeout(() => mainWindow.loadURL('http://localhost:5173'), 2000);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }
}

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------
ipcMain.handle('get-platform', () => process.platform);
ipcMain.handle('open-file-location', (_, filePath) => {
  shell.showItemInFolder(filePath);
});
ipcMain.handle('minimize-window', () => mainWindow?.minimize());
ipcMain.handle('maximize-window', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow?.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});
ipcMain.handle('close-window', () => mainWindow?.close());

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------
app.whenReady().then(() => {
  startBackend();
  // Give backend 2s to boot before opening the window
  setTimeout(createWindow, isDev ? 500 : 2000);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
  if (process.platform !== 'darwin') app.quit();
});
