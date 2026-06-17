import fs from 'node:fs/promises'
import path from 'node:path'

import { getPayload } from 'payload'

import config from '../src/payload.config'

type SeedRow = {
  objectID: string
  departmentSlug: string
  laneKey: string
  editorialTitle: string
  sortOrder: string
  targetState: string
  artistName: string
  artistSlug: string
  artworkSlug: string
  departmentName: string
  departmentSourceID: string
  readyForHighlight: string
  primaryImagePresent: string
  publicDomain: string
  objectURL: string
}

function parseCsv(text: string): SeedRow[] {
  const [headerLine, ...lines] = text.trim().split('\n')
  const headers = headerLine.split(',')
  return lines
    .filter(Boolean)
    .map((line) => {
      const values = line.split(',')
      return headers.reduce((acc, key, index) => {
        acc[key as keyof SeedRow] = values[index] || ''
        return acc
      }, {} as SeedRow)
    })
}

async function main() {
  const workspaceRoot = process.cwd()
  const dataRoot = path.resolve(workspaceRoot, '../data')
  const runtimeRoot = path.resolve(workspaceRoot, 'runtime')
  const outputRoot = path.resolve(workspaceRoot, 'output')

  await fs.mkdir(runtimeRoot, { recursive: true })
  await fs.mkdir(outputRoot, { recursive: true })

  await fs.rm(path.resolve(runtimeRoot, 'payload.db'), { force: true })
  await fs.rm(path.resolve(runtimeRoot, 'payload.db-shm'), { force: true })
  await fs.rm(path.resolve(runtimeRoot, 'payload.db-wal'), { force: true })

  const lanesPayload = JSON.parse(await fs.readFile(path.resolve(dataRoot, 'audience_lanes.json'), 'utf8'))
  const detailsLines = (await fs.readFile(path.resolve(dataRoot, 'met_object_details.ndjson'), 'utf8'))
    .trim()
    .split('\n')
    .filter(Boolean)
    .map((line) => JSON.parse(line))
  const usersPayload = JSON.parse(await fs.readFile(path.resolve(dataRoot, 'seed_users.json'), 'utf8'))
  const seedRows = parseCsv(await fs.readFile(path.resolve(dataRoot, 'met_objects_seed.csv'), 'utf8'))

  const detailsById = new Map(detailsLines.map((item) => [String(item.objectID), item]))
  const payload = await getPayload({ config })

  for (const user of usersPayload.users) {
    await payload.create({
      collection: 'users',
      data: user,
      overrideAccess: true,
    })
  }

  const departments = new Map<string, unknown>()
  for (const row of seedRows) {
    if (departments.has(row.departmentSlug)) {
      continue
    }

    const doc = await payload.create({
      collection: 'departments',
      data: {
        name: row.departmentName,
        slug: row.departmentSlug,
        sourceDepartmentId: row.departmentSourceID ? Number.parseInt(row.departmentSourceID, 10) : null,
      },
      overrideAccess: true,
    })

    departments.set(row.departmentSlug, doc.id)
  }

  const artists = new Map<string, unknown>()
  for (const row of seedRows) {
    if (artists.has(row.artistSlug)) {
      continue
    }

    const details = detailsById.get(row.objectID)
    const doc = await payload.create({
      collection: 'artists',
      data: {
        name: row.artistName,
        slug: row.artistSlug,
        bio: details?.artistDisplayBio || '',
      },
      overrideAccess: true,
    })

    artists.set(row.artistSlug, doc.id)
  }

  const artworks = new Map<string, unknown>()
  for (const row of seedRows) {
    const details = detailsById.get(row.objectID)
    const doc = await payload.create({
      collection: 'artworks',
      data: {
        objectID: Number.parseInt(row.objectID, 10),
        title: details.title,
        slug: row.artworkSlug,
        artist: artists.get(row.artistSlug),
        department: departments.get(row.departmentSlug),
        objectDate: details.objectDate || '',
        objectURL: details.objectURL || row.objectURL,
        primaryImage: details.primaryImageSmall || '',
        isPublicDomain: row.publicDomain === 'true',
        readyForHighlight: row.readyForHighlight === 'true',
      },
      overrideAccess: true,
    })

    artworks.set(row.objectID, doc.id)
  }

  const laneDocs = new Map<string, unknown>()
  for (const lane of lanesPayload.lanes) {
    const doc = await payload.create({
      collection: 'highlight-lanes',
      data: {
        laneKey: lane.key,
        title: lane.title,
        audience: lane.audience,
        summary: lane.summary,
        departments: lane.departmentSlugs.map((slug: string) => departments.get(slug)).filter(Boolean),
      },
      overrideAccess: true,
    })

    laneDocs.set(lane.key, doc.id)
  }

  let publishedHighlights = 0
  for (const row of seedRows) {
    const shouldPublish = row.targetState === 'publish'
    if (shouldPublish) {
      publishedHighlights += 1
    }

    await payload.create({
      collection: 'highlights',
      data: {
        headline: row.editorialTitle,
        slug: `${row.laneKey}-${row.objectID}`,
        lane: laneDocs.get(row.laneKey),
        artwork: artworks.get(row.objectID),
        sortOrder: Number.parseInt(row.sortOrder, 10),
        _status: shouldPublish ? 'published' : 'draft',
      },
      overrideAccess: true,
    })
  }

  await fs.writeFile(
    path.resolve(outputRoot, 'seed-summary.json'),
    JSON.stringify(
      {
        departments: departments.size,
        artists: artists.size,
        artworks: artworks.size,
        highlightLanes: laneDocs.size,
        publishedHighlights,
      },
      null,
      2,
    ),
    'utf8',
  )
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
