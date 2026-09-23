export function hasRole(user: any, roles: string[]): boolean {
  return Boolean(user && roles.includes(user.role))
}

export function isSignedIn({ req }: any): boolean {
  return Boolean(req.user)
}

export function canManageCatalog({ req }: any): boolean {
  return hasRole(req.user, ['admin', 'curator'])
}

export function canEditHighlights({ req }: any): boolean {
  return hasRole(req.user, ['admin', 'curator', 'editor'])
}

export function publicHighlightRead({ req }: any): boolean | Record<string, unknown> {
  if (req.user) {
    return true
  }

  return {
    and: [
      {
        _status: {
          equals: 'published',
        },
      },
      {
        'artwork.readyForHighlight': {
          equals: true,
        },
      },
    ],
  }
}
