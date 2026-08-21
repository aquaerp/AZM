const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('azmDesktop', {
  apiBaseUrl: ipcRenderer.sendSync('azm:get-api-base-url'),
  saveApiBaseUrl: (value) => ipcRenderer.invoke('azm:save-api-base-url', value),
})
