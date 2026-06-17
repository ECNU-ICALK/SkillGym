import config from '@payload-config'
import '@payloadcms/next/css'
import type { ServerFunctionClient } from 'payload'
import { handleServerFunctions, RootLayout } from '@payloadcms/next/layouts'
import React from 'react'

import { importMap } from './admin/importMap.js'

const serverFunction: ServerFunctionClient = async function (args) {
  'use server'

  return handleServerFunctions({
    ...args,
    config,
    importMap,
  })
}

export default function PayloadLayout(props: { children: React.ReactNode }) {
  return (
    <RootLayout config={config} importMap={importMap} serverFunction={serverFunction}>
      {props.children}
    </RootLayout>
  )
}
