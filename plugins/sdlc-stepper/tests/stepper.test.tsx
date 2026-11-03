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

// The marks of the stages and parts on the terminal band, in order: ✓ done, ● current, ○ not started, ◌ blocked
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const marks = async (ui: any): Promise<string[]> => (await ui.findAll({ type: 'Text', text: /^[✓●○◌]$/ })).map((t: { text: string }) => t.text)

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
  // The terminal draws one row in an outline: a mini stepper (a mark per stage, joined by short lines) where the title
  // would be, then where the session is now
  expect(await marks(ui)).toEqual(['✓', '●', '○', '○'])  // Define, Build, Review, Ship
  expect(await ui.findAll({ type: 'Text', text: /^─$/ })).toHaveLength(3)
  expect(await ui.find({ type: 'Text', text: 'SDLC' })).toBeUndefined()  // no title: the stepper is the title
  expect((await ui.find({ type: 'Text', text: /B2/ }))?.text).toBe('Build · B2 Title row · failing tests')
  expect(await ui.find({ type: 'Text', text: /parts|■|□/ })).toBeUndefined()
  expect((await ui.find({ type: 'Text', text: /B2/ }))?.props.wrap).toBe('truncate-end')  // cut with an ellipsis when too long
  // All of it sits in a rounded outline, and the current stage is green like the done ones (no orange accent)
  expect((await ui.findAll({ type: 'Box' })).some(b => b.props.borderStyle === 'round')).toBe(true)
  expect((await ui.find({ type: 'Text', text: '●' }))?.props.color).toBe('success')
  await ui.unmount()

  // The desktop draws one row: a mini stepper (the four stages as small icons joined by short lines, one drawing)
  // where a title would be, a dot, where the session is now, and the feature at the right
  const card = await $.ui.mount({ ...BAND, surface: 'desktop' })
  const drawings = await card.findAll({ type: 'Svg' })
  expect(drawings).toHaveLength(1)
  const mini = String(drawings[0]?.props.source)
  expect(drawings[0]?.props.alt).toBe('Define: done, Build: in progress, Review: not started, Ship: not started')
  expect(drawings[0]?.props.height).toBe(20)
  expect(mini.match(/<svg x=/g)).toHaveLength(4)  // an icon per stage
  expect(mini.match(/data-line='done'/g)).toHaveLength(1)   // Define to Build: the work is past Define
  expect(mini.match(/data-line='ahead'/g)).toHaveLength(2)  // Build to Review, Review to Ship
  expect(mini.match(/<rect data-line=[^>]*height='1'/g)).toHaveLength(3)  // 1px
  expect(mini).toContain('<path')                           // a done stage holds a check
  // Only the current icon pulses: its ring spreads out and fades
  expect(mini.match(/attributeName='r'/g)).toHaveLength(1)
  expect(mini.match(/<animate/g)).toHaveLength(2)
  expect(mini).not.toContain('fill-opacity=\'0\'>')  // no tint behind anything
  expect([...new Set(mini.match(/#[0-9a-f]{3,6}/gi) ?? [])].sort()).toEqual(['#2DA44E', '#7C828C', '#fff'])
  expect(await card.find({ type: 'Text', text: 'SDLC' })).toBeUndefined()  // no title: the stepper is the title
  expect((await card.find({ type: 'Text', text: '·' }))?.text).toBe('·')  // the dot between the stepper and where it is
  expect((await card.find({ type: 'Text', text: /B2/ }))?.text).toBe('Build · B2  Title row · failing tests')
  // The words are cut with an ellipsis when too long, and the feature keeps its place at the right
  expect((await card.find({ type: 'Text', text: /B2/ }))?.props.wrap).toBe('truncate-end')
  expect((await card.find({ type: 'Text', text: /2026-11-03-m-github-look/ }))?.props.wrap).toBe('truncate-start')
  expect(await card.find({ type: 'Text', text: /parts/ })).toBeUndefined()
  expect(await card.find({ type: 'Text', text: /✓|●/ })).toBeUndefined()  // no terminal glyphs on desktop
  await card.unmount()
})

test("the bar shows the agent's latest update line, so it says what the transcript says", async ($, on) => {
  repo(on, {
    '.sdlc/config.json': '{}',
    '.sdlc/state/2026-11-03-m-github-look.md': STATE,
    '.sdlc/state/2026-11-03-m-github-look/backlog.md': BACKLOG,
  })
  // The engine beneath: the model's response to a step, with whatever it said
  let said = ''
  on('turn.step', async function* (_, e) {
    return { turnId: e.turnId, index: e.index, answer: said, toolUses: [], stopReason: 'end_turn', usage: null }
  })
  const step = async (answer: string) => {
    said = answer
    for await (const _ of $.turn.step({ turnId: 't1', index: 0, model: 'sonnet', messageCount: 1 })) void _
  }
  const words = async (surface: 'terminal' | 'desktop') => {
    const ui = await $.ui.mount({ ...BAND, surface })
    const text = (await ui.find({ type: 'Text', text: /^Build · / }))?.text
    await ui.unmount()
    return text
  }
  await $.session.start({ cwd: '/repo', surface: 'desktop', isInteractive: true })
  await $.tool.call({ tool: 'Bash', command: 'python3 "/p/scripts/verify.py" red AC-002' })
  expect(await words('desktop')).toBe('Build · B2  Title row · failing tests')  // what the last tool said

  // The agent says something else: the bar says it too, on both surfaces, and a tool it doesn't know changes nothing
  await step('Looking at it.\n**Build · audit · checking where the theme sweep leaks**\nMore text.')
  expect(await words('desktop')).toBe('Build · audit · checking where the theme sweep leaks')
  expect(await words('terminal')).toBe('Build · audit · checking where the theme sweep leaks')
  await $.tool.call({ tool: 'mcp__browser__page_script', script: 'x' })
  expect(await words('desktop')).toBe('Build · audit · checking where the theme sweep leaks')

  // The last such line of a response wins; text with none leaves it; a line for another phase is not this feature's
  await step('Build · audit · first\nBuild · audit · second')
  expect(await words('desktop')).toBe('Build · audit · second')
  await step('Nothing to report.')
  expect(await words('desktop')).toBe('Build · audit · second')
  await step('Review · B2 · checking')
  expect(await words('desktop')).toBe('Build · audit · second')

  // A tool the bar knows is newer than a line: it names the step again
  await $.tool.call({ tool: 'Bash', command: 'python3 "/p/scripts/verify.py"' })
  expect(await words('desktop')).toBe('Build · B2  Title row · verify')
})

test('on the terminal the outline goes when the band is given fewer than 3 rows, so it still shows', async ($, on) => {
  repo(on, { '.sdlc/config.json': '{}', '.sdlc/state/f.md': STATE })
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  for (const [maxRows, framed] of [[10, true], [3, true], [2, false], [1, false]] as const) {
    const ui = await $.ui.mount({ ...BAND, props: { ...BAND.props, maxRows }, surface: 'terminal' })
    expect((await ui.findAll({ type: 'Box' })).some(b => b.props.borderStyle === 'round')).toBe(framed)
    expect(await marks(ui)).toEqual(['✓', '●', '○', '○'])  // the stepper is there either way
    await ui.unmount()
  }
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
    const order = ['Define', 'Build', 'Review', 'Ship']
    expect(await marks(ui)).toEqual(order.map((_, i) => (i < order.indexOf(phase) ? '✓' : i === order.indexOf(phase) ? '●' : '○')))
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
  expect(await marks(ui)).toEqual(['✓', '✓', '●', '○'])  // in Review now
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
  expect(await marks(ui)).toEqual(['✓', '✓', '●', '○'])
  expect((await ui.find({ type: 'Text', text: /github-look/ }))?.text).toBe('worktrees/web · github-look')
  await ui.unmount()
})
