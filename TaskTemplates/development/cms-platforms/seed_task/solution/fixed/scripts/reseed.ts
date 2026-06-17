import fs from 'node:fs/promises'
import path from 'node:path'

import { getPayload } from 'payload'

import config from '../src/payload.config'

type SeedRow = {
  artistName: string
  artistSlug: string
  artworkSlug: string
  departmentName: string
  departmentSlug: string
  departmentSourceID: string
  editorialTitle: string
  laneKey: string
  objectID: string
  objectURL: string
  primaryImagePresent: string
  publicDomain: string
  readyForHighlight: string
  sortOrder: string
  targetState: string
}

function parseCsv(text: string): SeedRow[] {
  const [headerLine, ...lines] = text.trim().split('\n')
  const headers = headerLine.trim().split(',') as Array<keyof SeedRow>

  return lines
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const values = line.split(',')
      return headers.reduce((acc, key, index) => {
        acc[key] = values[index]?.trim() || ''
        return acc
      }, {} as SeedRow)
    })
}

function isReadyForHighlight(isPublicDomain: boolean, primaryImage: string): boolean {
  return isPublicDomain && Boolean(primaryImage.trim())
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

  const users = new Map<string, number>()
  for (const user of usersPayload.users) {
    const doc = await payload.create({
      collection: 'users',
      data: user,
      overrideAccess: true,
    })
    users.set(user.email, doc.id)
  }

  const departments = new Map<string, number>()
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

  const artists = new Map<string, number>()
  for (const row of seedRows) {
    if (artists.has(row.artistSlug)) {
      continue
    }

    const details = detailsById.get(row.objectID)
    const doc = await payload.create({
      collection: 'artists',
      data: {
        bio: details?.artistDisplayBio || '',
        name: details?.artistDisplayName || row.artistName,
        slug: row.artistSlug,
      },
      overrideAccess: true,
    })
    artists.set(row.artistSlug, doc.id)
  }

  const artworks = new Map<string, { id: number; readyForHighlight: boolean; departmentId: number | null }>()
  for (const row of seedRows) {
    const details = detailsById.get(row.objectID)
    const primaryImage = String(details?.primaryImageSmall || '').trim()
    const isPublicDomain = Boolean(details?.isPublicDomain)
    const doc = await payload.create({
      collection: 'artworks',
      data: {
        objectID: Number.parseInt(row.objectID, 10),
        title: details?.title || row.editorialTitle,
        slug: row.artworkSlug,
        artist: artists.get(row.artistSlug),
        department: departments.get(row.departmentSlug),
        objectDate: details?.objectDate || '',
        objectURL: details?.objectURL || row.objectURL,
        primaryImage,
        isPublicDomain,
        readyForHighlight: isReadyForHighlight(isPublicDomain, primaryImage),
      },
      overrideAccess: true,
    })

    artworks.set(row.objectID, {
      id: doc.id,
      readyForHighlight: doc.readyForHighlight,
      departmentId: departments.get(row.departmentSlug) ?? null,
    })
  }

  const laneDocs = new Map<string, { id: number; departmentIds: number[] }>()
  for (const lane of lanesPayload.lanes) {
    const departmentIds = lane.departmentSlugs.map((slug: string) => departments.get(slug)).filter(Boolean)
    const doc = await payload.create({
      collection: 'highlight-lanes',
      data: {
        laneKey: lane.key,
        title: lane.title,
        audience: lane.audience,
        summary: lane.summary,
        departments: departmentIds,
      },
      overrideAccess: true,
    })

    laneDocs.set(lane.key, {
      id: doc.id,
      departmentIds,
    })
  }

  const defaultOwner = users.get('editor@metfeed.local') ?? null
  let publishedHighlights = 0
  for (const row of seedRows) {
    const artwork = artworks.get(row.objectID)
    const lane = laneDocs.get(row.laneKey)
    const laneAllowsDepartment = Boolean(
      lane && artwork?.departmentId && lane.departmentIds.includes(artwork.departmentId),
    )
    const shouldPublish = Boolean(row.targetState === 'publish' && artwork?.readyForHighlight && laneAllowsDepartment)

    await payload.create({
      collection: 'highlights',
      data: {
        headline: row.editorialTitle,
        slug: `${row.laneKey}-${row.objectID}`,
        lane: lane?.id,
        artwork: artwork?.id,
        owner: defaultOwner,
        sortOrder: Number.parseInt(row.sortOrder, 10),
        _status: shouldPublish ? 'published' : 'draft',
      } as any,
      overrideAccess: true,
    })

    if (shouldPublish) {
      publishedHighlights += 1
    }
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
