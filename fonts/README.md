Source fonts (latin subsets, WOFF) from the Fontsource packages @fontsource/instrument-serif,
@fontsource/geist-sans and @fontsource/geist-mono, version 5.3.0. All are SIL Open Font License 1.1.
`scripts/svgkit.py` subsets these per card with pyftsubset and embeds them as base64 WOFF.
It reads each file's name table and OS/2 table first and refuses to build if the family, weight
or italic flag differs from what the card code expects.
