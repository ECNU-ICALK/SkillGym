import type { CollectionConfig } from 'payload'

import { canEditHighlights, canReadHighlights, canUpdateHighlights } from '../lib/auth'
import { slugify } from '../lib/slugify'

async function findById(req: any, collection: string, value: any) {
  const id = typeof value === 'object' ? value?.id : value
  if (!id) {
    return null
  }

  return req.payload.findByID({
    collection,
    id,
    depth: 0,
    overrideAccess: true,
  })
}

export const Highlights: CollectionConfig = {
  slug: 'highlights',
  access: {
    create: canEditHighlights,
    delete: ({ req }) => ['admin', 'curator'].includes(req.user?.role),
    read: canReadHighlights,
    update: canUpdateHighlights,
  },
  admin: {
    useAsTitle: 'headline',
  },
  versions: {
    drafts: true,
  },
  hooks: {
    beforeChange: [
      async ({ data, operation, originalDoc, req }) => {
        const nextData = { ...data }
        const userRole = req.user?.role
        const nextStatus = nextData._status || originalDoc?._status || 'draft'
        const isCreate = operation === 'create'

        if (!nextData.slug && typeof nextData.headline === 'string' && nextData.headline.trim()) {
          nextData.slug = slugify(nextData.headline)
        }

        if (isCreate && !nextData.owner && req.user?.id) {
          nextData.owner = req.user.id
        }

        if (userRole === 'editor') {
          const nextSortOrder = nextData.sortOrder ?? originalDoc?.sortOrder
          nextData.owner = isCreate ? req.user?.id : originalDoc?.owner ?? req.user?.id

          if (nextStatus === 'published') {
            throw new Error('Editors cannot publish highlights.')
          }

          if (!isCreate && originalDoc && nextSortOrder !== originalDoc.sortOrder) {
            throw new Error('Editors cannot change highlight ordering.')
          }

          if (isCreate && nextData.sortOrder !== undefined) {
            nextData.sortOrder = 999
          }
        }

        const artworkDoc = await findById(req, 'artworks', nextData.artwork || originalDoc?.artwork)
        const laneDoc = await findById(req, 'highlight-lanes', nextData.lane || originalDoc?.lane)

        if (nextStatus === 'published' && !artworkDoc?.readyForHighlight) {
          throw new Error('Only ready artworks may enter the public feed.')
        }

        if (nextStatus === 'published' && artworkDoc && laneDoc) {
          const artworkDepartmentId =
            typeof artworkDoc.department === 'object' ? artworkDoc.department?.id : artworkDoc.department
          const laneDepartmentIds = Array.isArray(laneDoc.departments)
            ? laneDoc.departments.map((value: any) => (typeof value === 'object' ? value?.id : value)).filter(Boolean)
            : []

          if (artworkDepartmentId && laneDepartmentIds.length > 0 && !laneDepartmentIds.includes(artworkDepartmentId)) {
            throw new Error('Published highlights must stay within the selected lane department scope.')
          }
        }

        return nextData
      },
    ],
  },
  fields: [
    {
      name: 'headline',
      type: 'text',
      required: true,
    },
    {
      name: 'slug',
      type: 'text',
      required: true,
      unique: true,
    },
    {
      name: 'lane',
      type: 'relationship',
      relationTo: 'highlight-lanes',
      required: true,
    },
    {
      name: 'artwork',
      type: 'relationship',
      relationTo: 'artworks',
      required: true,
    },
    {
      name: 'owner',
      type: 'relationship',
      relationTo: 'users',
      required: true,
    },
    {
      name: 'sortOrder',
      type: 'number',
      defaultValue: 999,
    },
  ],
}
