---
name: astropy
description: |
  Core Python package for astronomy data analysis, covering coordinates, units, FITS, WCS,
  time systems, tables, cosmology, constants, and astronomical image handling.
risk: unknown
source: https://github.com/astropy/astropy
license: BSD-3-Clause
---

# Astropy

## When to Use This Skill

Use astropy when tasks involve:
- Converting between celestial coordinate systems
- Working with physical units and quantities
- Reading, writing, or manipulating FITS files
- Cosmological calculations such as luminosity distance
- Precise time handling with ISO, JD, MJD, and UTC
- Table operations such as catalog reading, filtering, joining, and cross-matching
- WCS transformations between pixel and world coordinates
- Astronomical constants and calculations

## Core Capabilities

- `astropy.units`: units and quantity arithmetic
- `astropy.coordinates`: sky coordinates and angular separations
- `astropy.io.fits`: FITS file access and headers
- `astropy.table`: table I/O and catalog handling
- `astropy.time`: precise times and scale conversions
- `astropy.wcs`: image WCS transformations
- `astropy.cosmology`: cosmological distances and related calculations

## Best Practices

- Attach units to quantities before arithmetic.
- Use `SkyCoord` for separations and frame conversions.
- Use `Time` for UTC and MJD handling.
- Read FITS headers before applying WCS or exposure metadata.
- Prefer table joins or catalog matching for association tasks.

