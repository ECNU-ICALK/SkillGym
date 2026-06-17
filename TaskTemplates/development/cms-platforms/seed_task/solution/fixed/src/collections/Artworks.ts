import type { CollectionConfig } from 'payload'

import { canManageCatalog, isSignedIn } from '../lib/auth'

function isReadyForHighlight(data: { isPublicDomain?: boolean; primaryImage?: string | null }): boolean {
  return Boolean(data.isPublicDomain) && Boolean((data.primaryImage || '').trim())
}

export const Artworks: CollectionConfig = {
  slug: 'artworks',
  access: {
    create: canManageCatalog,
    delete: canManageCatalog,
    read: isSignedIn,
    update: canManageCatalog,
  },
  admin: {
    useAsTitle: 'title',
  },
  hooks: {
    beforeValidate: [
      ({ data, originalDoc }) => {
        const nextData = { ...data }
        const primaryImage = String(nextData.primaryImage ?? originalDoc?.primaryImage ?? '').trim()
        const isPublicDomain =
          typeof nextData.isPublicDomain === 'boolean'
            ? nextData.isPublicDomain
            : Boolean(originalDoc?.isPublicDomain)

        nextData.primaryImage = primaryImage
        nextData.readyForHighlight = isReadyForHighlight({
          isPublicDomain,
          primaryImage,
        })

        return nextData
      },
    ],
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
      admin: {
        readOnly: true,
      },
      defaultValue: false,
      required: true,
    },
  ],
}
