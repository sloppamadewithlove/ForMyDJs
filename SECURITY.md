# Security

ForMyDJ is a local-first app. The repo should not contain API keys, passwords,
private keys, user downloads, app build output, or machine-specific credentials.

## What Is Safe To Commit

- Source code, tests, docs, app assets, release workflows, and packaging scripts.
- Example configuration files with placeholder values only.

## What Must Stay Out Of Git

- `.env` files and local shell config.
- API keys, access tokens, passwords, private keys, certificates, and signing files.
- Downloaded tracks or local audio test files that are not intentional fixtures.
- Built app bundles, release ZIPs, caches, logs, and temporary conversion output.

The repo ignore rules cover the common local-secret and generated-output paths.

## Before Pushing

Run the same secret scanner used in CI:

```bash
gitleaks git --no-banner --redact --log-opts="--all" .
gitleaks dir --no-banner --redact .
```

Install Gitleaks on macOS with:

```bash
brew install gitleaks
```

The GitHub Actions security scan runs on pushes and pull requests. It checks
both git history and the current working tree.

## If A Secret Is Ever Committed

1. Revoke or rotate the exposed secret immediately. Removing it from a later
   commit is not enough.
2. Remove the secret from the repo files.
3. Rewrite repository history only after coordinating with contributors,
   because a force-push affects every clone and open branch.
4. Re-run Gitleaks on both history and the working tree before pushing again.
