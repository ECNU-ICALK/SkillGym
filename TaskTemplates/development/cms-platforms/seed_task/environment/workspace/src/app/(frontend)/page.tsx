export default function HomePage() {
  return (
    <main>
      <h1>Met Highlight Feed Workspace</h1>
      <p>Use the admin panel to manage content and the feed endpoint to inspect public output.</p>
      <ul>
        <li><a href="/admin">Admin</a></li>
        <li><a href="/api/highlight-lanes/feed">Public feed</a></li>
      </ul>
    </main>
  )
}
