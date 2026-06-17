import type { CollectionConfig } from 'payload'

import { canManageCatalog } from '../lib/auth'

export const Departments: CollectionConfig = {
  slug: 'departments',
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
      unique: true,
    },
    {
      name: 'slug',
      type: 'text',
      required: true,
      unique: true,
    },
    {
      name: 'sourceDepartmentId',
      type: 'number',
    },
  ],
}
