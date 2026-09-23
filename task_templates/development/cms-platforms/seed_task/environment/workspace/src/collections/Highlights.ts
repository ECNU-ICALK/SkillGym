import type { CollectionConfig } from 'payload'

import { canEditHighlights } from '../lib/auth'
import { slugify } from '../lib/slugify'

export const Highlights: CollectionConfig = {
  slug: 'highlights',
  access: {
    create: canEditHighlights,
    delete: ({ req }) => ['admin', 'curator'].includes(req.user?.role),
    read: () => true,
    update: canEditHighlights,
  },
  admin: {
    useAsTitle: 'headline',
  },
  versions: {
    drafts: true,
  },
  hooks: {
    beforeChange: [
      async ({ data }) => {
        const nextData = { ...data }

        if (!nextData.slug && typeof nextData.headline === 'string' && nextData.headline.trim()) {
          nextData.slug = slugify(nextData.headline)
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
      name: 'sortOrder',
      type: 'number',
      defaultValue: 999,
    },
  ],
}
