import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Phase, Step, View } from '../types'
import { PHASES, makeView, parseBacklog, parseState, stepFor, updateLine } from './sdlc'
import type { IconState } from './desktop'
import { MINI_H, miniSvg, phaseState } from './desktop'

const SHAPE = 'v2' // v2: View has `repo`
const view = atom({ plugin: 'sdlc-stepper', key: 'view' } as const, null, { shape: SHAPE })
const step = atom({ plugin: 'sdlc-stepper', key: 'step' } as const, null, { shape: SHAPE })

async function text($: EngineInterface, path: string): Promise<string | null> {
  try {
    const t = await $.fs.read(path)
    return typeof t === 'string' ? t : null
  } catch {
    return null
  }
}

async function entries($: EngineInterface, path: string) {
  try {
    return await $.fs.list(path)
  } catch {
    return []
  }
}

// Folders never holding a repo of the user's: skipped when the session starts above its repos
const SKIP = new Set(['node_modules', 'dist', 'build', 'target', 'vendor', 'coverage'])
const MAX_REPOS = 50

/** The sdlc repos this session works in: its own folder ('') when it is one, else the folders up to two levels
 *  below it with `.sdlc/config.json` (a workbench of several repos and worktrees, as product-rebuild starts in). */
async function findRepos($: EngineInterface): Promise<string[]> {
  if (await $.fs.exists('.sdlc/config.json')) return ['']
  const found: string[] = []
  for (const a of await entries($, '.')) {
    if (a.kind !== 'dir' || a.name.startsWith('.') || SKIP.has(a.name)) continue
    if (await $.fs.exists(`${a.name}/.sdlc/config.json`)) {
      found.push(a.name)
      continue
    }
    for (const b of await entries($, a.name)) {
      if (b.kind !== 'dir' || b.name.startsWith('.') || SKIP.has(b.name)) continue
      if (await $.fs.exists(`${a.name}/${b.name}/.sdlc/config.json`)) found.push(`${a.name}/${b.name}`)
      if (found.length >= MAX_REPOS) return found
    }
  }
  return found
}

/** The active feature across those repos, the most recently touched when there are several; null with none. */
async function load($: EngineInterface, repos: string[]): Promise<View | null> {
  const candidates: { repo: string; name: string; state: string; backlog: string; mtime: number }[] = []
  for (const repo of repos) {
    const at = repo ? `${repo}/` : ''
    for (const e of await entries($, `${at}.sdlc/state`)) {
      if (e.kind === 'file' && e.name.endsWith('.md')) {
        const name = e.name.slice(0, -3)
        candidates.push({ repo, name, state: `${at}.sdlc/state/${e.name}`, backlog: `${at}.sdlc/state/${name}/backlog.md`, mtime: e.mtimeMs })
      }
    }
    for (const e of await entries($, `${at}.sdlc`)) {
      if (e.kind === 'dir' && !['state', '.work', 'ci'].includes(e.name)) {
        candidates.push({ repo, name: e.name, state: `${at}.sdlc/${e.name}/state.md`, backlog: `${at}.sdlc/${e.name}/backlog.md`, mtime: e.mtimeMs })
      }
    }
  }
  let best: { v: View; mtime: number } | null = null
  for (const c of candidates) {
    if (best && best.mtime >= c.mtime) continue
    const s = await text($, c.state)
    const parsed = s ? parseState(c.name, s) : null
    if (!parsed) continue
    const b = await text($, c.backlog)
    best = { v: makeView(c.repo, parsed.feature, parsed.phase, b ? parseBacklog(b) : []), mtime: c.mtime }
  }
  return best ? best.v : null
}

// Found at session start and on each prompt, reused by every tool call between (a reload finds them again)
let repos: string[] | null = null

async function refresh($: EngineInterface, rescan = false): Promise<View | null> {
  let next: View | null = null
  try {
    if (rescan || repos === null) repos = await findRepos($)
    next = repos.length ? await load($, repos) : null
  } catch {
    next = null
  }
  await update($, view, prev => (JSON.stringify(prev) === JSON.stringify(next) ? prev : next))
  return next
}

/** Keep the agent's latest update (the line it begins with `<Phase> · `), from what the model just said, as the
 *  bar's words, so the bar says what the transcript says. A tool the bar knows replaces it, being newer. */
async function noteUpdate($: EngineInterface, answer: string): Promise<void> {
  const found = updateLine(answer)
  if (!found) return
  const v = await read($, view)
  if (!v || found.phase !== v.phase) return  // a line for another phase isn't this feature's words
  await update($, step, prev => ({ phase: found.phase, name: prev && prev.phase === found.phase ? prev.name : '', line: found.line }))
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const out = await next(e)
    await refresh($, true)
    return out
  })

  // The band only reads: a failure here must never hold a prompt or a tool call
  on('prompt.submit', async ($, e, next) => {
    await refresh($, true)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('tool.call', async ($, e, next) => {
    const out = await next(e)
    try {
      const v = await refresh($)
      if (v && out.deny === undefined) {
        const name = stepFor(v.phase, e.tool, e as unknown as Record<string, unknown>)
        if (name) await update($, step, () => ({ phase: v.phase, name }) satisfies Step)
      }
    } catch {
      // a stale band is better than a failed tool call
    }
    return out
  }).catch(($, e, next) => next(e))

  // The model's response, step by step: the bar follows the update line in it. It only reads; the stream passes on whole.
  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    try {
      await noteUpdate($, result.answer)
    } catch {
      // a stale bar is better than a failed step
    }
    return result
  })

  on('turn.complete', async ($, e, next) => {
    await refresh($)
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const v = await read($, view)
    if (e.props.hasSurvey || !v) return next(e)
    const s = await read($, step)
    const stepName = s && s.phase === v.phase ? s.name : null
    const said = s && s.phase === v.phase ? s.line : undefined  // the agent's own latest update, when it has made one

    if (e.surface === 'desktop') {
      // One row drawn straight onto the app's own band: a mini stepper (the four stages as small icons joined by
      // short lines, one drawing) where a title would be, a dot, where the session is now (phase, part, step), and
      // the feature at the right. Only the current stage's icon pulses.
      const { Box, Text, Svg } = $.ui.resolve(e)
      const mini = miniSvg(v.phase)
      // After the stepper: the phase, then the part and the step when there are any, so it is never bare
      const here = said ?? [v.phase, v.current ? `${v.current.id}  ${v.current.title}` : null, stepName].filter(Boolean).join(' · ')
      return (
        <Box flexDirection="row" alignItems="center" gap={2} paddingX={1}>
          {/* The words take the room left and are cut with an ellipsis when too long; the feature keeps its own */}
          <Box flexDirection="row" alignItems="center" gap="xs" width={0} flexGrow={1}>
            <Svg source={mini.source} alt={mini.alt} width={mini.width} height={MINI_H} />
            <Text size="caption" dimColor>·</Text>
            <Box width={0} flexGrow={1}>
              <Text size="caption" wrap="truncate-end">{here}</Text>
            </Box>
          </Box>
          <Box flexShrink={0}>
            <Text key="feature" size="caption" dimColor wrap="truncate-start">
              {`${v.repo ? `${v.repo} · ` : ''}${v.feature}`}
            </Text>
          </Box>
        </Box>
      )
    }

    // The terminal band is one row in a rounded outline (3 rows with it; the engine gives the band only the rows left
    // above the prompt and hides a band that doesn't fit, so with fewer than 3 it is the row alone): a mini stepper (the four stages as marks joined by short
    // lines, green once passed) where the title would be, then where the session is now (phase, part, step), with
    // the feature at the right. Done and current are both green, told apart by the mark (✓ and ●). Nothing pulses.
    const { Box, Text } = $.ui.resolve(e)
    const at = PHASES.indexOf(v.phase)
    const width = e.props.bodyColumns ?? 80
    const narrow = width < 60
    const framed = (e.props.maxRows ?? 3) >= 3
    const mark = (state: IconState) => (state === 'done' ? '✓' : state === 'current' ? '●' : state === 'blocked' ? '◌' : '○')
    const tone = (state: IconState) => (state === 'done' || state === 'current' ? 'success' : state === 'blocked' ? 'warning' : 'inactive')

    const mini = PHASES.flatMap((p: Phase, i) => {
      const state = phaseState(i, at)
      const out = [<Text key={p} color={tone(state)}>{mark(state)}</Text>]
      if (i < PHASES.length - 1) out.push(<Text key={`${p}-line`} color={i < at ? 'success' : 'inactive'} dimColor={i >= at}>{'─'}</Text>)
      return out
    })

    // After the stepper: the phase, then the part and the step when there are any, so it is never bare
    const here = said ?? [
      v.phase,
      v.current ? `${v.current.id}${v.current.title ? ` ${v.current.title}` : ''}` : null,
      stepName,
    ].filter(Boolean).join(' · ')

    return (
      <Box flexDirection="column" borderStyle={framed ? 'round' : undefined} borderColor="inactive" paddingX={framed ? 1 : 0}>
        <Box flexDirection="row">
          {/* The words take the room left and are cut with an ellipsis when too long; the feature keeps its own */}
          <Box flexDirection="row" width={0} flexGrow={1}>
            {mini}
            <Text dimColor>{' · '}</Text>
            <Box width={0} flexGrow={1}>
              <Text wrap="truncate-end">{here}</Text>
            </Box>
          </Box>
          {!narrow && (
            <Box paddingLeft={2} flexShrink={0}>
              <Text dimColor wrap="truncate-start">{`${v.repo ? `${v.repo} · ` : ''}${v.feature}`}</Text>
            </Box>
          )}
        </Box>
      </Box>
    )
  })
}
