import type { CollectionConfig } from 'payload'

import { canManageCatalog } from '../lib/auth'

export const Artworks: CollectionConfig = {
  slug: 'artworks',
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
      name: 'objectID',
      type: 'number',
      required: true,
      unique: true,
    },
    {
      name: 'title',
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
      name: 'artist',
      type: 'relationship',
      relationTo: 'artists',
      required: true,
    },
    {
      name: 'department',
      type: 'relationship',
      relationTo: 'departments',
      required: true,
    },
    {
      name: 'objectDate',
      type: 'text',
      required: true,
    },
    {
      name: 'objectURL',
      type: 'text',
      required: true,
    },
    {
      name: 'primaryImage',
      type: 'text',
    },
    {
      name: 'isPublicDomain',
      type: 'checkbox',
      defaultValue: false,
      required: true,
    },
    {
      name: 'readyForHighlight',
      type: 'checkbox',
      defaultValue: false,
      required: true,
    },
  ],
}
