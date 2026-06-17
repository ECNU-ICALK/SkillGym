import React from 'react'

export const metadata = {
  title: 'Met Highlight Feed',
  description: 'Local Payload CMS task workspace',
}

export default function RootLayout(props: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'Georgia, serif', margin: 0, padding: '2rem', background: '#f5f0e8' }}>
        {props.children}
      </body>
    </html>
  )
}
