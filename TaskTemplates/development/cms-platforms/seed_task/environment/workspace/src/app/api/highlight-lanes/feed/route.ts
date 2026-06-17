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
  const limit = toPositiveInt(request.nextUrl.searchParams.get('limit'))

  const result = await payload.find({
    collection: 'highlights',
    depth: 2,
    limit: limit || 100,
    overrideAccess: true,
    pagination: false,
    sort: 'sortOrder',
  })

  const items = result.docs
    .map((doc: any) => {
      const lane = typeof doc.lane === 'object' ? doc.lane : null
      const artwork = typeof doc.artwork === 'object' ? doc.artwork : null
      const artist = artwork && typeof artwork.artist === 'object' ? artwork.artist : null
      const dept = artwork && typeof artwork.department === 'object' ? artwork.department : null

      if (!lane || !artwork || !artist || !dept) {
        return null
      }

      return {
        laneKey: lane.laneKey,
        lane: lane.title,
        title: doc.headline,
        slug: doc.slug,
        artistName: artist.name,
        department: dept.name,
        objectDate: artwork.objectDate,
        primaryImage: artwork.primaryImage,
        objectURL: artwork.objectURL,
        sortOrder: doc.sortOrder,
      }
    })
    .filter(Boolean)
    .sort((left: any, right: any) => {
      return left.laneKey.localeCompare(right.laneKey) || left.sortOrder - right.sortOrder || left.slug.localeCompare(right.slug)
    })
    .map(({ laneKey: _laneKey, ...item }: any) => item)

  return NextResponse.json({
    total: items.length,
    items,
  })
}
