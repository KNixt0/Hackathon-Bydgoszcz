# Third-party licences: services/frontend

Allowed by `coord/GUIDELINES.md` rule 2: MIT, Apache-2.0, BSD, ISC (no GPL / AGPL / LGPL). Fonts and icons are openly licensed.
Versions are pinned in `package.json` and `package-lock.json`. Regenerate this file when a dependency changes.

## Runtime dependencies (direct)

| Package | Version | Licence | Used for |
|---|---|---|---|
| @fontsource/ibm-plex-sans | 5.3.0 | OFL-1.1 | Self-hosted UI typeface (IBM Plex Sans, latin + latin-ext) |
| @radix-ui/react-dialog | 1.3.1 | MIT | Accessible dialog / drawer primitive |
| @radix-ui/react-dropdown-menu | 2.2.1 | MIT | Accessible menu primitive |
| @radix-ui/react-slider | 1.6.1 | MIT | Threshold slider primitive |
| @radix-ui/react-tabs | 1.2.1 | MIT | Tabs primitive |
| cmdk | 1.1.1 | MIT | Command palette (Cmd+K) |
| lucide-react | 1.77.0 | ISC | Icons |
| react | 19.3.1 | MIT | UI library |
| react-dom | 19.3.1 | MIT | DOM renderer |
| react-router-dom | 7.18.6 | MIT | Routing and deep links |
| recharts | 3.11.0 | MIT | Charts |
| socket.io-client | 4.8.4 | MIT | Live updates (Socket.IO) |

Notes:

- **IBM Plex Sans** is licensed under the SIL Open Font License 1.1 (OFL-1.1), an open font licence. The font files are bundled into the build and served from the same origin; nothing is loaded from a CDN.
- **lucide-react** icons are ISC (a few icons derived from Feather are MIT).

## Runtime dependencies (transitive)

Everything the direct dependencies pull in for production (92 packages). Licences present: MIT, ISC, BSD-3-Clause, 0BSD.

| Package | Version | Licence |
|---|---|---|
| @floating-ui/core | 1.8.0 | MIT |
| @floating-ui/dom | 1.8.0 | MIT |
| @floating-ui/react-dom | 2.1.9 | MIT |
| @floating-ui/utils | 0.2.12 | MIT |
| @radix-ui/number | 1.1.3 | MIT |
| @radix-ui/primitive | 1.2.0 | MIT |
| @radix-ui/react-arrow | 1.1.17 | MIT |
| @radix-ui/react-collection | 1.2.0 | MIT |
| @radix-ui/react-compose-refs | 1.1.5 | MIT |
| @radix-ui/react-context | 1.3.0 | MIT |
| @radix-ui/react-direction | 1.2.0 | MIT |
| @radix-ui/react-dismissable-layer | 1.2.1 | MIT |
| @radix-ui/react-focus-guards | 1.2.0 | MIT |
| @radix-ui/react-focus-scope | 1.3.1 | MIT |
| @radix-ui/react-id | 1.1.4 | MIT |
| @radix-ui/react-menu | 2.2.1 | MIT |
| @radix-ui/react-popper | 1.4.0 | MIT |
| @radix-ui/react-portal | 1.2.0 | MIT |
| @radix-ui/react-presence | 1.1.11 | MIT |
| @radix-ui/react-primitive | 2.2.0 | MIT |
| @radix-ui/react-roving-focus | 1.2.1 | MIT |
| @radix-ui/react-slot | 1.5.0 | MIT |
| @radix-ui/react-use-callback-ref | 1.1.5 | MIT |
| @radix-ui/react-use-controllable-state | 1.3.0 | MIT |
| @radix-ui/react-use-effect-event | 0.0.5 | MIT |
| @radix-ui/react-use-is-hydrated | 0.1.3 | MIT |
| @radix-ui/react-use-layout-effect | 1.1.4 | MIT |
| @radix-ui/react-use-rect | 1.1.4 | MIT |
| @radix-ui/react-use-size | 1.1.5 | MIT |
| @radix-ui/rect | 1.1.3 | MIT |
| @reduxjs/toolkit | 2.15.0 | MIT |
| @socket.io/component-emitter | 3.1.2 | MIT |
| @standard-schema/spec | 1.1.0 | MIT |
| @standard-schema/utils | 0.3.0 | MIT |
| @types/d3-array | 3.2.2 | MIT |
| @types/d3-color | 3.1.3 | MIT |
| @types/d3-ease | 3.0.2 | MIT |
| @types/d3-interpolate | 3.0.4 | MIT |
| @types/d3-path | 3.1.1 | MIT |
| @types/d3-scale | 4.0.9 | MIT |
| @types/d3-shape | 3.2.0 | MIT |
| @types/d3-time | 3.0.4 | MIT |
| @types/d3-timer | 3.0.2 | MIT |
| @types/react | 19.3.0 | MIT |
| @types/react-dom | 19.3.0 | MIT |
| @types/use-sync-external-store | 0.0.6 | MIT |
| aria-hidden | 1.2.6 | MIT |
| clsx | 2.1.1 | MIT |
| cookie | 1.1.1 | MIT |
| csstype | 3.2.4 | MIT |
| d3-array | 3.2.5 | ISC |
| d3-color | 3.1.1 | ISC |
| d3-ease | 3.0.2 | BSD-3-Clause |
| d3-format | 3.1.3 | ISC |
| d3-interpolate | 3.0.2 | ISC |
| d3-path | 3.1.1 | ISC |
| d3-scale | 4.0.3 | ISC |
| d3-shape | 3.2.1 | ISC |
| d3-time | 3.1.1 | ISC |
| d3-time-format | 4.1.1 | ISC |
| d3-timer | 3.0.2 | ISC |
| debug | 4.4.3 | MIT |
| decimal.js-light | 2.5.1 | MIT |
| detect-node-es | 1.1.0 | MIT |
| engine.io-client | 6.6.8 | MIT |
| engine.io-parser | 5.2.3 | MIT |
| es-toolkit | 1.53.2 | MIT |
| eventemitter3 | 5.0.4 | MIT |
| get-nonce | 1.0.1 | MIT |
| immer | 11.2.10 | MIT |
| internmap | 2.0.3 | ISC |
| ms | 2.1.3 | MIT |
| react-is | 19.3.1 | MIT |
| react-redux | 9.3.1 | MIT |
| react-remove-scroll | 2.7.2 | MIT |
| react-remove-scroll-bar | 2.3.8 | MIT |
| react-router | 7.18.6 | MIT |
| react-style-singleton | 2.2.3 | MIT |
| redux | 5.0.1 | MIT |
| redux-thunk | 3.1.0 | MIT |
| reselect | 5.2.0 | MIT |
| scheduler | 0.28.0 | MIT |
| set-cookie-parser | 2.7.3 | MIT |
| socket.io-parser | 4.2.7 | MIT |
| tiny-invariant | 1.3.3 | MIT |
| tslib | 2.9.1 | 0BSD |
| use-callback-ref | 1.3.3 | MIT |
| use-sidecar | 1.1.3 | MIT |
| use-sync-external-store | 1.7.0 | MIT |
| victory-vendor | 37.4.1 | MIT AND ISC AND BSD-3-Clause |
| ws | 8.21.3 | MIT |
| xmlhttprequest-ssl | 2.1.2 | MIT |

## Build and test tooling (not shipped)

Dev dependencies are used only to build, lint and test; none of their code is part of the production bundle or the Docker runtime image (nginx serves static files only).

| Tool | Licence |
|---|---|
| vite, @vitejs/plugin-react, vitest, jsdom | MIT |
| typescript | Apache-2.0 |
| eslint, @eslint/js, typescript-eslint, eslint-plugin-react-hooks, globals | MIT |
| @testing-library/react, @testing-library/user-event, @testing-library/jest-dom | MIT |
| socket.io (dev mock server only) | MIT |
| @types/* | MIT |

Transitive build-time-only packages under other licences: `lightningcss` (MPL-2.0, CSS minifier binary used by Vite), `caniuse-lite` (CC-BY-4.0, browser data), `minimatch` / `lru-cache` (BlueOak-1.0.0). They run on the build machine and are not distributed with the product.

## Runtime image

`nginxinc/nginx-unprivileged` (nginx: BSD-2-Clause) on Alpine Linux.
