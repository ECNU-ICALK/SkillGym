import type { CollectionConfig } from 'payload'

import { canManageCatalog } from '../lib/auth'

export const Artists: CollectionConfig = {
  slug: 'artists',
  access: {
    create: canManageCatalog,
    delete: canManageCatalog,
    read: () => true,
    update: canManageCatalog,
  },
  admin: {
    useAsTitle: 'name',
  },
  fields: [
    {
      name: 'name',
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
      name: 'bio',
      type: 'textarea',
    },
  ],
}
