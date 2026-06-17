import type { CollectionConfig } from 'payload'

import { canManageCatalog } from '../lib/auth'

export const HighlightLanes: CollectionConfig = {
  slug: 'highlight-lanes',
  access: {
    create: canManageCatalog,
    delete: canManageCatalog,
    read: () => true,
    update: canManageCatalog,
  },
  admin: {
    useAsTitle: 'title',
  },
  fields: [
    {
      name: 'laneKey',
      type: 'text',
      required: true,
      unique: true,
    },
    {
      name: 'title',
      type: 'text',
      required: true,
    },
    {
      name: 'audience',
      type: 'text',
      required: true,
    },
    {
      name: 'summary',
      type: 'textarea',
      required: true,
    },
    {
      name: 'departments',
      type: 'relationship',
      hasMany: true,
      relationTo: 'departments',
      required: true,
    },
  ],
}
