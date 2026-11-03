import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Phase, Step, View } from '../types'
import { PHASES, makeView, parseBacklog, parseState, stepFor } from './sdlc'
import { PART_ICON, PHASE_ICON, iconSvg, partAlt, partState, phaseAlt, phaseState } from './desktop'

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

  on('turn.complete', async ($, e, next) => {
    await refresh($)
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const v = await read($, view)
    if (e.props.hasSurvey || !v) return next(e)
    const s = await read($, step)
    const stepName = s && s.phase === v.phase ? s.name : null
    const total = v.parts.length
    const finished = v.parts.filter(p => p.status.startsWith('done')).length

    if (e.surface === 'desktop') {
      // A card of two rows, all neutral: the words (SDLC, where it is now, the feature), then one bar across the
      // full width. The bar is each phase's icon and name joined by lines that stretch to fill the row; Build's
      // line carries one small icon per part. Icons are SVG; names and lines are text, so they follow the theme.
      const { Box, Text, Svg } = $.ui.resolve(e)
      const at = PHASES.indexOf(v.phase)
      const buildAt = PHASES.indexOf('Build')
      // A line as wide as the room it is given: a run of box-drawing dashes in a one-row box that clips it
      const rule = (key: string, solid: boolean, grow = 1) => (
        <Box key={key} width={0} flexGrow={grow} height={1} overflow="hidden">
          <Text color={solid ? undefined : 'inactive'} dimColor={!solid}>{'─'.repeat(240)}</Text>
        </Box>
      )
      const items: unknown[] = []
      PHASES.forEach((p: Phase, i) => {
        const state = phaseState(i, at)
        items.push(
          <Box key={p} flexDirection="row" alignItems="center" gap="sm">
            <Svg source={iconSvg(state)} alt={phaseAlt(p, state)} width={PHASE_ICON} height={PHASE_ICON} />
            <Text size="footnote" weight={state === 'current' ? 'semibold' : 'medium'} dimColor={state === 'todo'}>{p}</Text>
          </Box>,
        )
        if (i === PHASES.length - 1) return
        if (i === buildAt && total > 0) {
          // Build's line: a small icon per part, each with the line up to it solid once the work has reached it
          const parts: unknown[] = []
          v.parts.forEach(part => {
            const state = partState(part, v.current)
            parts.push(rule(`${part.id}-in`, at > buildAt || state !== 'todo' && state !== 'blocked'))
            parts.push(<Svg key={part.id} source={iconSvg(state)} alt={partAlt(part, state)} width={PART_ICON} height={PART_ICON} />)
          })
          parts.push(rule('parts-out', at > buildAt || finished === total))
          items.push(
            <Box key={`${p}-parts`} flexDirection="row" alignItems="center" width={0} flexGrow={3} gap="xs">{parts}</Box>,
          )
        } else {
          items.push(rule(`${p}-line`, at > i))
        }
      })

      const here = [v.current ? `${v.current.id}  ${v.current.title}` : null, stepName].filter(Boolean).join(' · ')
      return (
        <Box flexDirection="column" borderStyle="round" borderColor="promptBorder" backgroundColor="inverseText" paddingX={2} paddingY={1} gap={1}>
          <Box flexDirection="row" justifyContent="space-between" alignItems="center" gap={2}>
            <Box flexDirection="row" alignItems="center" gap={2} flexShrink={1}>
              <Text size="caption" weight="semibold">SDLC</Text>
              {here && <Text size="caption" dimColor wrap="truncate-end">{here}</Text>}
            </Box>
            <Text key="feature" size="caption" dimColor wrap="truncate-start">
              {`${v.repo ? `${v.repo} · ` : ''}${v.feature}`}
            </Text>
          </Box>
          <Box flexDirection="row" alignItems="center" gap="sm">{items}</Box>
        </Box>
      )
    }

    const { Box, Text } = $.ui.resolve(e)
    const at = PHASES.indexOf(v.phase)
    const width = e.props.bodyColumns ?? 80
    const narrow = width < 60

    const stepper = PHASES.flatMap((p: Phase, i) => {
      const done = i < at
      const now = i === at
      const mark = done ? '✓' : now ? '●' : '○'
      const out = [
        <Text key={p} color={done ? 'success' : now ? 'claude' : 'inactive'} bold={now}>
          {mark} {p}
        </Text>,
      ]
      if (i < PHASES.length - 1) out.push(<Text key={`${p}-line`} color={done ? 'success' : 'inactive'}>{narrow ? ' ─ ' : ' ─── '}</Text>)
      return out
    })

    const where = [
      v.current ? `${v.current.id}${v.current.title ? ` ${v.current.title}` : ''}` : null,
      stepName,
    ].filter(Boolean).join(' · ')

    return (
      <Box flexDirection="column">
        <Box flexDirection="row">
          <Text dimColor>sdlc </Text>
          {stepper}
          {!narrow && <Text dimColor wrap="truncate-end">{`   ${v.repo ? `${v.repo} · ` : ''}${v.feature}`}</Text>}
        </Box>
        {(total > 0 || where) && (
          <Box flexDirection="row">
            {total > 0 && <Text color="success">{'■'.repeat(finished)}</Text>}
            {total > 0 && <Text color="inactive">{'□'.repeat(total - finished)}</Text>}
            {total > 0 && <Text dimColor>{` ${finished}/${total} parts`}</Text>}
            {where && <Text wrap="truncate-end">{`${total > 0 ? '  ·  ' : ''}${where}`}</Text>}
          </Box>
        )}
      </Box>
    )
  })
}
