# Generic Spider Templates

Most crawls fall into one of two patterns: "follow links matching this regex" or "crawl every URL listed in the site's sitemap". Scrapling ships templates for both so you don't have to hand-write the same `parse()` boilerplate every time.

Both templates build on `LinkExtractor`, which pulls URLs out of a `Response` (or filters a single URL via `matches()`). `SitemapSpider` additionally parses sitemap.xml / sitemap_index.xml bodies internally (gzip-compressed or not).

You can use `LinkExtractor` directly inside any plain `Spider.parse()`. The templates just save you the wiring.

## CrawlSpider

`CrawlSpider` follows links automatically based on declarative rules.

```python
from scrapling.spiders import CrawlSpider, CrawlRule, LinkExtractor

class BlogCrawler(CrawlSpider):
    name = "blog"
    start_urls = ["https://example.com"]

    def rules(self):
        return [
            CrawlRule(LinkExtractor(allow=r"/posts/"), callback=self.parse_post),
            CrawlRule(LinkExtractor(allow=r"/page/\d+/")),  # follow pagination, no callback
        ]

    async def parse_post(self, response):
        yield {
            "title": response.css("h1::text").get(),
            "url": response.url,
        }

result = BlogCrawler().start()
```

A `CrawlRule` pairs a `LinkExtractor` with an optional `callback` (a bound method on the spider), an optional `priority` override for the dispatched `Request`, and an optional `process_request` (a bound method that mutates each `Request` before it's yielded). The default `parse()` runs every rule against every response and yields a `Request` per matched URL.

If a rule has no callback, the matched URLs fall through to the spider's default `parse()` (or stay uncallback'd if you didn't override it). This is convenient for pagination: extract the next-page links to keep the crawl going, but don't need a separate handler.

### Combining rules with custom logic

Override `parse()` and call `super().parse(response)` to get the rule behavior plus your own yields:

```python
class MySpider(CrawlSpider):
    def rules(self):
        return [CrawlRule(LinkExtractor(allow=r"/posts/"), callback=self.parse_post)]

    async def parse(self, response):
        yield {"page_url": response.url}
        async for req in super().parse(response):
            yield req
```

### Mutating Requests with `process_request`

```python
def add_priority(self, request, response):
    request.priority = 10
    return request

def rules(self):
    return [CrawlRule(
        LinkExtractor(allow=r"/posts/"),
        callback=self.parse_post,
        process_request=self.add_priority,
    )]
```

## SitemapSpider

`SitemapSpider` seeds a crawl from sitemap.xml URLs. It uses the same `rules()` API as `CrawlSpider`, so the mental model is shared.

```python
from scrapling.spiders import SitemapSpider, CrawlRule, LinkExtractor

class MySitemap(SitemapSpider):
    name = "sm"
    sitemap_urls = ["https://example.com/sitemap.xml"]

    def rules(self):
        return [
            CrawlRule(LinkExtractor(allow=r"/posts/"), callback=self.parse_post),
            CrawlRule(LinkExtractor(allow=r"/products/"), callback=self.parse_product),
        ]

    async def parse_post(self, response):
        yield {"title": response.css("h1::text").get()}

    async def parse_product(self, response):
        yield {"sku": response.css(".sku::text").get()}

result = MySitemap().start()
```

### How URLs are dispatched

For each URL in the sitemap, `SitemapSpider` checks every rule's `LinkExtractor.matches(url)` in order. The first matching rule wins, and a `Request` is yielded with that rule's callback. If no rule matches and `rules()` is non-empty, the URL is dropped (matches Scrapy's behavior). If `rules()` returns an empty list, every URL is routed to the spider's `parse()` method, which raises `NotImplementedError` by default - override it to handle them.

### Sitemap indexes

When `SitemapSpider` encounters a `<sitemapindex>` (a sitemap of sitemaps), it descends into each child sitemap automatically. To filter which child sitemaps to descend into, set `sitemap_follow` to a `LinkExtractor`:

```python
class MySitemap(SitemapSpider):
    name = "sm"
    sitemap_urls = ["https://example.com/sitemap.xml"]
    sitemap_follow = LinkExtractor(allow=r"/posts-sitemap-\d+\.xml")  # only post sitemaps
```

### Robots.txt support

Put a `robots.txt` URL directly in `sitemap_urls` and `SitemapSpider` will detect it, extract every `Sitemap:` directive (via `protego`), and follow each one:

```python
class MySitemap(SitemapSpider):
    name = "sm"
    sitemap_urls = ["https://example.com/robots.txt"]  # Sitemap: directives discovered automatically
```

### Alternate-language URLs

Set `sitemap_alternate_links = True` to also dispatch `<xhtml:link rel="alternate" hreflang="...">` URLs through your rules.

## Using `LinkExtractor` directly

You don't have to use the templates. `LinkExtractor` works inside any plain `Spider`:

```python
from scrapling.spiders import Spider, LinkExtractor

class CustomSpider(Spider):
    name = "custom"
    start_urls = ["https://example.com"]

    def __init__(self):
        super().__init__()
        self._links = LinkExtractor(allow=r"/posts/", deny_domains="ads.example.com")

    async def parse(self, response):
        for url in self._links.extract(response):
            yield response.follow(url, callback=self.parse_post)

    async def parse_post(self, response):
        yield {"title": response.css("h1::text").get()}
```

## LinkExtractor reference

| Argument | Default | Description |
|---|---|---|
| `allow` | `()` | URL patterns to keep. Empty means "match all". String, compiled `Pattern`, or iterable of either. |
| `deny` | `()` | URL patterns to drop. Always overrides `allow`. |
| `allow_domains` | `()` | Hostnames to keep. Subdomains match automatically (`example.com` matches `api.example.com`). |
| `deny_domains` | `()` | Hostnames to drop. |
| `restrict_css` | `()` | CSS selectors that scope DOM extraction to a region. |
| `restrict_xpath` | `()` | XPath selectors that scope DOM extraction to a region. |
| `tags` | `("a", "area")` | Element tags to look for links in. |
| `attrs` | `("href",)` | Attributes on those tags to read URLs from. |
| `canonicalize` | `True` | Sort query params and normalize the path. |
| `strip` | `True` | Strip whitespace from extracted URLs. |
| `keep_fragment` | `False` | Preserve the `#fragment` when canonicalizing. |
| `deny_extensions` | `IGNORED_EXTENSIONS` | File extensions to drop (pdf, zip, images, video, etc.). |
| `process` | `None` | Optional callable applied to each extracted URL before filtering. Return a falsy value to drop. |

`LinkExtractor.extract(response)` returns a `list[str]` of absolute, filtered, deduped URLs.

`LinkExtractor.matches(url)` returns a `bool` - the URL-only filter (allow/deny/domain/extension), used by `SitemapSpider` to dispatch URLs without a `Response`.
