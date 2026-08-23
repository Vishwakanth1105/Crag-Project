export interface HighlightRange {
  start: number
  end: number
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Builds a flexible-whitespace regex from an evidence snippet and returns the
 * non-overlapping character ranges it matches in the document text. Whitespace
 * inside snippets is matched as `\s+` so chunk boundaries, newlines, and page
 * breaks do not break highlighting.
 */
export function buildRanges(text: string, snippets: string[]): HighlightRange[] {
  const ranges: HighlightRange[] = []
  const seen = new Set<string>()
  for (const rawSnippet of snippets) {
    const snippet = rawSnippet.trim()
    if (snippet.length < 8) continue
    const pattern = escapeRegex(snippet).replace(/\s+/g, '\\s+')
    let regex: RegExp
    try {
      regex = new RegExp(pattern, 'gi')
    } catch {
      continue
    }
    for (const match of text.matchAll(regex)) {
      if (match.index === undefined) continue
      const key = `${match.index}:${match.index + match[0].length}`
      if (seen.has(key)) continue
      seen.add(key)
      ranges.push({ start: match.index, end: match.index + match[0].length })
    }
  }
  return mergeRanges(ranges)
}

export function mergeRanges(ranges: HighlightRange[]): HighlightRange[] {
  if (ranges.length === 0) return []
  const sorted = [...ranges].sort((a, b) => a.start - b.start || b.end - a.end)
  const merged: HighlightRange[] = [{ ...sorted[0] }]
  for (const range of sorted.slice(1)) {
    const last = merged[merged.length - 1]
    if (range.start <= last.end) {
      last.end = Math.max(last.end, range.end)
    } else {
      merged.push({ ...range })
    }
  }
  return merged
}

export interface TextSegment {
  value: string
  highlighted: boolean
}

export function splitIntoSegments(text: string, ranges: HighlightRange[]): TextSegment[] {
  const segments: TextSegment[] = []
  let cursor = 0
  for (const range of ranges) {
    if (range.start > cursor) {
      segments.push({ value: text.slice(cursor, range.start), highlighted: false })
    }
    segments.push({ value: text.slice(range.start, range.end), highlighted: true })
    cursor = range.end
  }
  if (cursor < text.length) {
    segments.push({ value: text.slice(cursor), highlighted: false })
  }
  return segments
}
