const { app, BrowserWindow, ipcMain, net, protocol, session } = require('electron')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')

protocol.registerSchemesAsPrivileged([{ scheme: 'azm', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } }])

// The desktop client must not inherit stale localhost proxy variables or a
// disabled system proxy. All API traffic already uses HTTPS to the configured
// Azm server, so a direct Electron network session is the predictable default.
app.commandLine.appendSwitch('no-proxy-server')

const settingsPath = () => path.join(app.getPath('userData'), 'settings.json')
const productionApiBaseUrl = 'https://tidesight.cloud/api'

function readSettings() {
  try { return JSON.parse(fs.readFileSync(settingsPath(), 'utf8')) } catch { return {} }
}

function normalizeApiBaseUrl(value) {
  const url = new URL(value.trim())
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('استخدم عنوان HTTP أو HTTPS صالحاً.')
  url.pathname = `${url.pathname.replace(/\/$/, '')}/api`.replace(/\/api\/api$/, '/api')
  return url.toString().replace(/\/$/, '')
}

function saveSettings(settings) {
  fs.mkdirSync(path.dirname(settingsPath()), { recursive: true })
  fs.writeFileSync(settingsPath(), JSON.stringify(settings), 'utf8')
}

ipcMain.on('azm:get-api-base-url', (event) => { event.returnValue = readSettings().apiBaseUrl || productionApiBaseUrl })
ipcMain.handle('azm:save-api-base-url', (_event, value) => {
  const apiBaseUrl = normalizeApiBaseUrl(value)
  saveSettings({ ...readSettings(), apiBaseUrl })
  return apiBaseUrl
})

function createWindow() {
  const window = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 980,
    minHeight: 680,
    backgroundColor: '#f4f7fa',
    webPreferences: { contextIsolation: true, nodeIntegration: false, preload: path.join(__dirname, 'preload.cjs') },
  })
  window.loadURL('azm://app/index.html')
}

app.whenReady().then(async () => {
  await session.defaultSession.setProxy({ mode: 'direct' })
  protocol.handle('azm', (request) => {
    const relativePath = decodeURIComponent(new URL(request.url).pathname).replace(/^\/+/, '') || 'index.html'
    const rendererRoot = path.resolve(__dirname, 'renderer')
    const filePath = path.resolve(rendererRoot, relativePath)
    if (!filePath.startsWith(`${rendererRoot}${path.sep}`) && filePath !== path.join(rendererRoot, 'index.html')) return new Response('Not found', { status: 404 })
    return net.fetch(pathToFileURL(filePath).toString())
  })
  createWindow()
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
})

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
