---
name: blogwatcher
description: Use this skill when you need to monitor blogs or RSS/Atom feeds for updates, new posts, or content changes using the blogwatcher CLI. This skill covers installation, feed discovery, adding blogs, scanning for articles, marking items as read or unread, filtering by blog, and cleaning up tracked blogs from the local database.
---

# Blogwatcher

Use `blogwatcher` to watch blogs and feed sources from the terminal.

## Installation

Install the CLI:

```bash
go install github.com/Hyaxia/blogwatcher/cmd/blogwatcher@latest
```

Confirm the installation:

```bash
blogwatcher --help
```

## When to use this skill

Use this skill when you need to:
- Add blogs or feed sources to a local watch list
- Discover and scan RSS/Atom feeds for new articles
- Review tracked blogs and unread items from the terminal
- Mark articles as read or unread
- Filter results for a specific blog
- Remove blogs from the local watch list

## Core workflow

### Add a blog

```bash
blogwatcher add "My Blog" https://example.com
```

### List tracked blogs

```bash
blogwatcher blogs
```

### Scan for articles

```bash
blogwatcher scan
```

### List articles

```bash
blogwatcher articles
```

### Mark an article as read

```bash
blogwatcher read 1
```

### Mark all articles as read

```bash
blogwatcher read-all
```

### Mark an article as unread

```bash
blogwatcher unread 1
```

### Remove a tracked blog

```bash
blogwatcher remove "My Blog"
```

## Notes

- Use `blogwatcher <command> --help` for command-specific options.
- Prefer feed discovery and feed-native workflows before scraping fallbacks.
