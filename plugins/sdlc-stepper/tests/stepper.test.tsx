import type { On } from 'claude-code'
import { expect, test } from 'claude-code/testing'

const STATE = `# 2026-11-03-m-github-look
Status: active
Process: 3
Track: M
Current: Stage 2 – Build
`
const BACKLOG = `# Backlog

| ID | Slice | FRs | ACs | Deps | Size | Status |
|---|---|---|---|---|---|---|
| B1 | Header bar | — | 1 | — | S | done |
| B2 | Title row | — | 2 | B1 | S | in progress |
| B3 | Issue list | — | 3 | B2 | S | todo |
`

const BAND = {
  plugin: 'sdlc-stepper',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: true,
    maxRows: 10,
    bodyColumns: 100,
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

function repo(on: On, files: Record<string, string>, mtimes: Record<string, number> = {}) {
  const dirs: Record<string, { name: string; kind: 'file' | 'dir' }[]> = {}
  for (const path of Object.keys(files)) {
    const parts = path.split('/')
    for (let i = 1; i < parts.length; i++) {
      const dir = parts.slice(0, i).join('/')
      const entry = { name: parts[i] as string, kind: (i === parts.length - 1 ? 'file' : 'dir') as 'file' | 'dir' }
      const list = (dirs[dir] ??= [])
      if (!list.some(x => x.name === entry.name)) list.push(entry)
    }
  }
  // The kit resolves a relative path against the plugin's folder: the fake repo is matched by its tail
  // and its folder itself (the session's) is the root, learnt from the mod's first call
  let root = ''
  dirs['.'] = []
  for (const top of new Set(Object.keys(files).map(f => f.split('/')[0] as string))) {
    dirs['.'].push({ name: top, kind: top in files ? 'file' : 'dir' })
  }
  const rel = (path: string) =>
    path === root || path === '.' ? '.'
      : ([...Object.keys(files), ...Object.keys(dirs)].find(k => path === k || path.endsWith(`/${k}`)) ?? path)
  on('fs.exists', (_, e) => {
    if (!root && e.path.endsWith('/.sdlc/config.json')) root = e.path.slice(0, -'/.sdlc/config.json'.length)
    return { value: rel(e.path) in files || rel(e.path) in dirs }
  })
  on('fs.read', (_, e) => {
    const text = files[rel(e.path)]
    if (text === undefined) throw new Error(`ENOENT ${e.path}`)
    return { value: text }
  })
  on('fs.list', (_, e) => {
    const list = dirs[rel(e.path)]
    if (!list) throw new Error(`ENOENT ${e.path}`)
    return { value: list.map(x => ({ ...x, size: 0, mtimeMs: mtimes[`${rel(e.path)}/${x.name}`] ?? 1, isLink: false })) }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('tool.call', () => ({ result: {} }))
}

test('the band names the phase, the part and the step, on every surface that has it', async ($, on) => {
  repo(on, {
    '.sdlc/config.json': '{}',
    '.sdlc/state/2026-11-03-m-github-look.md': STATE,
    '.sdlc/state/2026-11-03-m-github-look/backlog.md': BACKLOG,
  })
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  await $.tool.call({ tool: 'Bash', command: 'python3 "/p/scripts/verify.py" red AC-002' })

  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /Define/ }))?.text).toBe('✓ Define')
  expect((await ui.find({ type: 'Text', text: /Build/ }))?.text).toBe('● Build')
  expect((await ui.find({ type: 'Text', text: /Review/ }))?.text).toBe('○ Review')
  expect((await ui.find({ type: 'Text', text: /parts/ }))?.text).toBe(' 1/3 parts')
  expect((await ui.find({ type: 'Text', text: /B2/ }))?.text).toBe('  ·  B2 Title row · failing tests')
  await ui.unmount()

  // The desktop draws a card of two rows: SDLC with where it is now, then one bar of icons (a phase's, and a
  // small one per part on Build's line), the names as text
  const card = await $.ui.mount({ ...BAND, surface: 'desktop' })
  const icons = await card.findAll({ type: 'Svg' })
  expect(icons.map(i => i.props.alt)).toEqual([
    'Define: done', 'Build: in progress',
    'B1: done', 'B2: in progress', 'B3: not started',
    'Review: not started', 'Ship: not started',
  ])
  expect(String(icons[1]?.props.source)).toContain("attributeName='r'")  // the current phase pulses
  expect(String(icons[0]?.props.source)).toContain('<path')              // a done one holds a check
  const colors = new Set(icons.flatMap(i => String(i.props.source).match(/#[0-9a-f]{3,6}/gi) ?? []))
  expect([...colors].sort()).toEqual(['#7C828C', '#fff'])  // neutral only: one gray and white, no hue
  expect((await card.find({ type: 'Text', text: 'Build' }))?.text).toBe('Build')
  expect((await card.find({ type: 'Text', text: /B2/ }))?.text).toBe('B2  Title row · failing tests')
  expect(await card.find({ type: 'Text', text: /parts/ })).toBeUndefined()  // the count is the icons now
  expect(await card.find({ type: 'Text', text: /✓|●/ })).toBeUndefined()  // no terminal glyphs on desktop
  await card.unmount()
})

test('outside an sdlc repo, or with no active feature, the band stays empty', async ($, on) => {
  repo(on, {
    '.sdlc/config.json': '{}',
    '.sdlc/state/old.md': STATE.replace('Status: active', 'Status: done'),
  })
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('engine')
  await ui.unmount()
})

// The phase name on the Current: line wins; without it the number is read by the file's Process: marker
for (const [process, stage, phase] of [['3', 'Stage 3', 'Review'], ['3', 'Stage 4', 'Ship'], ['2', 'Stage 5', 'Review'], ['2', 'Stage 4', 'Build']] as const) {
  test(`a Process: ${process} state file at "${stage}" with no name shows ${phase}`, async ($, on) => {
    repo(on, {
      '.sdlc/config.json': '{}',
      '.sdlc/state/f.md': STATE.replace('Process: 3', `Process: ${process}`).replace('Stage 2 – Build', stage),
    })
    await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
    const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
    expect((await ui.find({ type: 'Text', text: new RegExp(phase) }))?.text).toBe(`● ${phase}`)
    await ui.unmount()
  })
}

test('an unmarked state file is not shown', async ($, on) => {
  repo(on, {
    '.sdlc/config.json': '{}',
    '.sdlc/state/f.md': STATE.replace('Process: 3\n', ''),
  })
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('engine')
  await ui.unmount()
})

test('a step seen in an earlier phase is not shown in the next one', async ($, on) => {
  const files: Record<string, string> = {
    '.sdlc/config.json': '{}',
    '.sdlc/state/f.md': STATE,
  }
  repo(on, files)
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  await $.tool.call({ tool: 'Bash', command: 'git commit -m "feat: B2"' })
  files['.sdlc/state/f.md'] = STATE.replace('Stage 2 – Build', 'Stage 3 – Review')
  await $.tool.call({ tool: 'Bash', command: 'ls' })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /Review/ }))?.text).toBe('● Review')
  expect(await ui.find({ type: 'Text', text: /commit/ })).toBeUndefined()
  await ui.unmount()
})


test('a session started above the repos shows the one with the latest active feature', async ($, on) => {
  repo(on, {
    'api/.sdlc/config.json': '{}',
    'api/.sdlc/state/old.md': STATE.replace('Stage 2 – Build', 'Stage 1 – Define'),
    'worktrees/web/.sdlc/config.json': '{}',
    'worktrees/web/.sdlc/state/github-look.md': STATE.replace('Stage 2 – Build', 'Stage 3 – Review'),
    'node_modules/x/.sdlc/config.json': '{}',
  }, { 'worktrees/web/.sdlc/state/github-look.md': 5 })
  await $.session.start({ cwd: '/workbench', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /Review/ }))?.text).toBe('● Review')
  expect((await ui.find({ type: 'Text', text: /github-look/ }))?.text).toBe('   worktrees/web · github-look')
  await ui.unmount()
})
