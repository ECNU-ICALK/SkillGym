import type { CollectionConfig } from 'payload'

import { canReadUsers, isAdmin } from '../lib/auth'

export const Users: CollectionConfig = {
  slug: 'users',
  access: {
    create: isAdmin,
    delete: isAdmin,
    read: canReadUsers,
    update: isAdmin,
  },
  admin: {
    useAsTitle: 'email',
  },
  auth: true,
  fields: [
    {
      name: 'displayName',
      type: 'text',
      required: true,
    },
    {
      name: 'role',
      type: 'select',
      access: {
        create: isAdmin,
        update: isAdmin,
      },
      defaultValue: 'editor',
      options: ['admin', 'curator', 'editor'],
      required: true,
    },
  ],
}
