import { NextRequest, NextResponse } from 'next/server'
import { getPayload } from 'payload'

import config from '@payload-config'

function toPositiveInt(input: string | null): number | undefined {
  if (!input) {
    return undefined
  }

  const value = Number.parseInt(input, 10)
  if (Number.isNaN(value) || value <= 0) {
    return undefined
  }

  return value
}

export async function GET(request: NextRequest) {
  const payload = await getPayload({ config })
  const department = request.nextUrl.searchParams.get('department')
  const audience = request.nextUrl.searchParams.get('audience')
  const limit = toPositiveInt(request.nextUrl.searchParams.get('limit'))

  const result = await payload.find({
    collection: 'highlights',
    depth: 2,
    draft: false,
    limit: 100,
    overrideAccess: true,
    pagination: false,
    sort: 'sortOrder',
  })

  const items = result.docs
    .map((doc: any) => {
      if (doc._status !== 'published') {
        return null
      }

      const lane = typeof doc.lane === 'object' ? doc.lane : null
      const artwork = typeof doc.artwork === 'object' ? doc.artwork : null
      const artist = artwork && typeof artwork.artist === 'object' ? artwork.artist : null
      const dept = artwork && typeof artwork.department === 'object' ? artwork.department : null

      if (!lane || !artwork || !artist || !dept) {
        return null
      }

      const laneDepartmentIds = Array.isArray(lane.departments)
        ? lane.departments.map((value: any) => (typeof value === 'object' ? value?.id : value)).filter(Boolean)
        : []
      const artworkDepartmentId = typeof dept.id === 'number' ? dept.id : dept?.id

      if (!artwork.readyForHighlight) {
        return null
      }

      if (laneDepartmentIds.length > 0 && artworkDepartmentId && !laneDepartmentIds.includes(artworkDepartmentId)) {
        return null
      }

      return {
        laneKey: lane.laneKey,
        laneAudience: lane.audience,
        lane: lane.title,
        title: doc.headline,
        slug: doc.slug,
        artistName: artist.name,
        departmentSlug: dept.slug,
        department: dept.name,
        objectDate: artwork.objectDate,
        primaryImage: artwork.primaryImage,
        objectURL: artwork.objectURL,
        sortOrder: doc.sortOrder,
      }
    })
    .filter(Boolean)
    .filter((item: any) => {
      if (department && item.departmentSlug !== department) {
        return false
      }

      if (audience && item.laneAudience !== audience) {
        return false
      }

      return true
    })
    .sort((left: any, right: any) => {
      return left.laneKey.localeCompare(right.laneKey) || left.sortOrder - right.sortOrder || left.slug.localeCompare(right.slug)
    })
    .slice(0, limit || 100)
    .map(({ laneKey: _laneKey, laneAudience: _laneAudience, departmentSlug: _departmentSlug, ...item }: any) => item)

  return NextResponse.json({
    total: items.length,
    items,
  })
}
