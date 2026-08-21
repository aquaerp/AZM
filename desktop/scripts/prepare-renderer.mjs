import { cp, mkdir, rm } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const desktopRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const projectRoot = resolve(desktopRoot, '..')
const frontendRoot = resolve(projectRoot, 'frontend')
const rendererRoot = resolve(desktopRoot, 'renderer')
const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm'

execFileSync(npm, ['run', 'build'], { cwd: frontendRoot, stdio: 'inherit', shell: process.platform === 'win32', env: { ...process.env, VITE_STATIC_BASE: 'relative' } })
await rm(rendererRoot, { recursive: true, force: true })
await mkdir(rendererRoot, { recursive: true })
await cp(resolve(frontendRoot, 'dist'), rendererRoot, { recursive: true })
