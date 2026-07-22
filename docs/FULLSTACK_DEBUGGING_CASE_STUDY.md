# Debugging case study: a current TypeScript release broke the production build

> Real issue observed during this portfolio hardening run. The application and
> data remain an independent synthetic sample; this is not a client incident.

## Reproduction

The initial frontend lock used TypeScript `7.0.2`, which was the registry's
current release in the execution environment. Unit tests and `tsc --noEmit`
passed, but the required production command failed:

```bash
cd apps/web
npm run build
```

Next.js `16.2.11` compiled the source, then its build worker attempted to
reconfigure/install TypeScript and exited with:

```text
The "id" argument must be of type string. Received undefined
Next.js build worker exited with code: 1
```

## Root cause and decision

The problem was not application typing. It was an ecosystem compatibility gap
between the newly released compiler and the selected current Next.js build tool.
Keeping TypeScript 7 merely because it was newest would leave the only artifact
that matters—the production build—broken.

The dependency was pinned to TypeScript `5.9.3`, a supported stable compiler for
the selected Next.js line. No source behavior was weakened and strict mode
remained enabled.

## Regression evidence

After the pin and lockfile update:

```bash
npm run typecheck
npm test
npm run build
npm audit --audit-level=high
```

all completed successfully. The production result prerendered `/` and the final
audited dependency tree reported zero known vulnerabilities at the run snapshot.
CI repeats typecheck, component tests and production build from `npm ci` so a
future dependency change cannot rely on a warm developer tree.

## Related supply-chain finding

The first current Next.js dependency tree also reported one moderate PostCSS and
two high Sharp advisories. The lock now overrides those transitive packages to
patched current releases, and `npm audit --audit-level=high` is an explicit gate.
This is a snapshot control, not a promise that future advisories cannot appear.

## Remaining risk

- TypeScript 5.9 is intentionally not the registry's newest release at this
  snapshot; upgrades require the complete verification gate, not version-chasing.
- Next.js, PostCSS, Sharp, Node, and browser dependencies need ongoing advisory
  review.
- A passing local and CI build does not prove runtime security, accessibility,
  browser compatibility, or production deployment.
