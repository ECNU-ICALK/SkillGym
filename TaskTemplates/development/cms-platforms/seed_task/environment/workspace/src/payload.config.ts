import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { buildConfig } from 'payload'
import { sqliteAdapter } from '@payloadcms/db-sqlite'

import { Artists } from './collections/Artists'
import { Artworks } from './collections/Artworks'
import { Departments } from './collections/Departments'
import { HighlightLanes } from './collections/HighlightLanes'
import { Highlights } from './collections/Highlights'
import { Users } from './collections/Users'

const filename = fileURLToPath(import.meta.url)
const dirname = path.dirname(filename)

export default buildConfig({
  admin: {
    user: Users.slug,
    importMap: {
      baseDir: path.resolve(dirname),
    },
  },
  collections: [Users, Departments, Artists, Artworks, HighlightLanes, Highlights],
  db: sqliteAdapter({
    client: {
      url: process.env.DATABASE_URL || 'file:./runtime/payload.db',
    },
  }),
  secret: process.env.PAYLOAD_SECRET || 'met-highlight-secret',
  typescript: {
    outputFile: path.resolve(dirname, 'payload-types.ts'),
  },
})
