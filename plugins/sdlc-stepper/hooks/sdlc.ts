// What the band shows, read from an sdlc repo's own files and the session's tool calls. No `$` here: pure functions.
import type { Part, Phase, View } from '../types'

export const PHASES: Phase[] = ['Define', 'Build', 'Review', 'Ship']
// The stage numbers, by the state file's `Process:` marker: 2.x used 1, 4, 5 and 8, 3.0 uses 1 to 4. The phase name on
// the same line wins; the number is only the fallback.
const BY_NUMBER: Record<string, Record<string, Phase>> = {
  '2': { '1': 'Define', '4': 'Build', '5': 'Review', '8': 'Ship' },
  '3': { '1': 'Define', '2': 'Build', '3': 'Review', '4': 'Ship' },
}

/** The feature a state file describes, or null when it isn't an active sdlc 2.x or 3.x feature. */
export function parseState(name: string, text: string): { feature: string; phase: Phase } | null {
  const process = /^Process:\s*([23])\b/m.exec(text)?.[1]
  if (!/^Status:\s*active\b/m.test(text) || !process) return null
  const m = /^Current:\s*Stage\s*(\d+)\s*[–-]?\s*(\w+)?/m.exec(text)
  if (!m) return null
  const named = PHASES.find(p => p.toLowerCase() === (m[2] ?? '').toLowerCase())
  const phase = named ?? BY_NUMBER[process]?.[m[1] ?? '']
  return phase ? { feature: name, phase } : null
}

function cells(line: string): string[] {
  return line.trim().replace(/^\||\|$/g, '').split(/(?<!\\)\|/).map(c => c.trim())
}

/** backlog.md's parts, from the first table with ID and Status columns (as scripts/backlog.py reads it). */
export function parseBacklog(text: string): Part[] {
  const parts: Part[] = []
  let cols: { id: number; status: number; title: number } | null = null
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line.startsWith('|')) {
      if (cols && parts.length) break
      continue
    }
    const row = cells(line)
    if (!cols) {
      const names = row.map(c => c.toLowerCase())
      const id = names.indexOf('id'), status = names.indexOf('status')
      if (id >= 0 && status >= 0) cols = { id, status, title: names.indexOf('slice') }
      continue
    }
    if (/^[\s|:-]+$/.test(line) || row.length <= Math.max(cols.id, cols.status)) continue
    parts.push({
      id: (row[cols.id] ?? '').toUpperCase(),
      title: cols.title >= 0 ? (row[cols.title] ?? '').replace(/\\\|/g, '|') : '',
      status: (row[cols.status] ?? '').toLowerCase(),
    })
  }
  return parts
}

export function currentPart(parts: Part[]): Part | null {
  return parts.find(p => p.status.startsWith('in progress')) ?? parts.find(p => !p.status.startsWith('done')) ?? null
}

export function makeView(repo: string, feature: string, phase: Phase, parts: Part[]): View {
  return { repo, feature, phase, parts, current: phase === 'Build' ? currentPart(parts) : null }
}

/** The step a tool call shows the session on, or null when it says nothing new. */
export function stepFor(phase: Phase, tool: string, input: Record<string, unknown>): string | null {
  const command = typeof input.command === 'string' ? input.command : ''
  const path = typeof input.file_path === 'string' ? input.file_path : ''
  if (tool === 'Bash') {
    if (/verify\.py["']?\s+(--\S+\s+\S+\s+)*red\b/.test(command)) return 'failing tests'
    if (/ship\.py/.test(command)) return 'checks'
    if (/gh pr create/.test(command)) return 'PR'
    if (/gh pr checks/.test(command)) return 'CI'
    if (/git commit\b/.test(command)) return phase === 'Define' ? null : 'commit'
    if (/verify\.py(?!["']?\s+(--\S+\s+\S+\s+)*status)/.test(command)) return 'verify'
    if (/diff_stats\.py/.test(command)) return 'reviews'
    if (/brief\.py/.test(command)) return 'reading'
    if (/state\.py["']?.*\bslice\s+\S+\s+start\b/.test(command)) return 'plan'
    return null
  }
  if (tool === 'Agent' || tool === 'Skill') {
    const what = JSON.stringify(input)
    return /review|reviewer|qa-tester/i.test(what) && phase !== 'Define' ? 'reviews' : null
  }
  if ((tool === 'Write' || tool === 'Edit' || tool === 'MultiEdit') && path) {
    if (/plan-B\d+\.md$/.test(path)) return 'plan'
    if (/(^|\/)\.sdlc\//.test(path)) return null
    if (/(^|\/)docs\/sdlc\/changes\/|(^|\/)change\.md$/.test(path)) return phase === 'Define' ? 'change file' : null
    if (phase === 'Build') return /(\.|_)(test|spec)\.|(^|\/)(tests?|__tests__)\//.test(path) ? 'tests' : 'code'
    if (phase === 'Review') return 'fixes'
    return null
  }
  return null
}
