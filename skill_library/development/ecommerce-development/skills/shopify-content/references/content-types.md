# Shopify Content Types Reference

## API-Managed Content

### Pages

| Operation | Method | Endpoint/Mutation |
|-----------|--------|-------------------|
| List | GraphQL | `{ pages(first: 50) { edges { node { id title } } } }` |
| Create | GraphQL | `pageCreate(page: { ... })` |
| Update | GraphQL | `pageUpdate(page: { id, ... })` |
| Delete | GraphQL | `pageDelete(id: "...")` |

Fields: `title`, `handle`, `body` (HTML), `isPublished`, `seo { title description }`, `templateSuffix`

### Blogs & Articles

| Operation | Method | Endpoint/Mutation |
|-----------|--------|-------------------|
| List blogs | GraphQL | `{ blogs(first: 10) { edges { node { id title } } } }` |
| List articles | GraphQL | `{ articles(first: 50) { edges { node { id title } } } }` |
| Create article | GraphQL | `articleCreate(article: { blogId, ... })` |
| Update article | GraphQL | `articleUpdate(article: { id, ... })` |
| Delete article | GraphQL | `articleDelete(id: "...")` |

Article fields: `blogId`, `title`, `handle`, `contentHtml`, `author { name }`, `tags`, `isPublished`, `publishDate`, `seo`, `image { src altText }`

### Redirects

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List | REST | `GET /admin/api/2025-01/redirects.json` |
| Create | REST | `POST /admin/api/2025-01/redirects.json` |
| Update | REST | `PUT /admin/api/2025-01/redirects/{id}.json` |
| Delete | REST | `DELETE /admin/api/2025-01/redirects/{id}.json` |

Fields: `path` (from), `target` (to)

### Metaobjects

Custom structured content types (e.g. team members, FAQs, locations).

| Operation | Method |
|-----------|--------|
| Define type | `metaobjectDefinitionCreate` |
| Create entry | `metaobjectCreate` |
| Update entry | `metaobjectUpdate` |
| Query entries | `metaobjects(type: "custom_type")` |

## Browser-Only Operations

These have limited or no API support — use browser automation:

| Content | Admin URL | Notes |
|---------|-----------|-------|
| Navigation menus | `/admin/menus` | `menuUpdate` mutation exists but is limited |
| Theme editor | `/admin/themes/current/editor` | Visual layout, no API |
| Store policies | `/admin/settings/legal` | Privacy, terms, refund policies |
| Checkout customisation | `/admin/settings/checkout` | Checkout flow and fields |
| Notification templates | `/admin/settings/notifications` | Email/SMS templates |

## Content Best Practices

### Page Templates

Shopify themes can define custom page templates. Use `templateSuffix` to select one:

```json
{ "templateSuffix": "contact" }
```

This uses `page.contact.liquid` (or `.json` for Online Store 2.0 themes).

### Metaobject vs Metafield

| Use Case | Choose |
|----------|--------|
| Standalone content (FAQ page, team page) | Metaobject |
| Extra data on a product/page | Metafield |
| Repeatable structured entries | Metaobject |
| Single value on a resource | Metafield |
