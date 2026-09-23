export function hasRole(user: any, roles: string[]): boolean {
  return Boolean(user && roles.includes(user.role))
}

export function isSignedIn({ req }: any): boolean {
  return Boolean(req.user)
}

export function isAdmin({ req }: any): boolean {
  return hasRole(req.user, ['admin'])
}

export function canManageCatalog({ req }: any): boolean {
  return hasRole(req.user, ['admin', 'curator'])
}

export function canEditHighlights({ req }: any): boolean {
  return hasRole(req.user, ['admin', 'curator', 'editor'])
}

export function canUpdateHighlights({ req }: any): boolean | Record<string, unknown> {
  if (hasRole(req.user, ['admin', 'curator'])) {
    return true
  }

  if (!req.user?.id || req.user?.role !== 'editor') {
    return false
  }

  return {
    and: [
      {
        owner: {
          equals: req.user.id,
        },
      },
      {
        _status: {
          equals: 'draft',
        },
      },
    ],
  }
}

export function canReadUsers({ req }: any): boolean | Record<string, unknown> {
  if (hasRole(req.user, ['admin'])) {
    return true
  }

  if (!req.user?.id) {
    return false
  }

  return {
    id: {
      equals: req.user.id,
    },
  }
}

export function publicHighlightReadQuery(): Record<string, unknown> {
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

export function canReadHighlights({ req }: any): boolean | Record<string, unknown> {
  if (hasRole(req.user, ['admin', 'curator'])) {
    return true
  }

  if (req.user?.role === 'editor' && req.user?.id) {
    return {
      or: [
        publicHighlightReadQuery(),
        {
          owner: {
            equals: req.user.id,
          },
        },
      ],
    }
  }

  return publicHighlightReadQuery()
}

export function publicHighlightRead({ req }: any): boolean | Record<string, unknown> {
  if (req.user) {
    return canReadHighlights({ req })
  }

  return publicHighlightReadQuery()
}
