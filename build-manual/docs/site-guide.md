# Publishing and maintaining this site

The documentation is stored under `build-manual/`, rendered with MkDocs Material, and deployed to **https://tylerboni.github.io/jag/** through GitHub Actions.

## One-time GitHub configuration

1. Merge the open documentation pull request into the `master` branch.
2. In the repository go to **Settings → Pages → Build and deployment**, and select **GitHub Actions** as Source.
3. Check **Actions** for the workflow **Build and deploy Jaguar swap manual**. A push to `master` changing documentation or the workflow will build and deploy the site.
4. Visit the Pages URL after a successful deployment. Initial publication is not guaranteed until GitHub Pages is enabled and the workflow succeeds.

## Editing

- Edit Markdown in `build-manual/` through GitHub or git.
- Navigation, theme and website search are configured in the repository-root `mkdocs.yml`.
- To preview locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

- To verify the static build, run `python -m mkdocs build --clean`.
- Pull requests run a build check; only pushes to `master` deploy.

## Editing safety

Do not publish a pinout, wire color, torque, CAN payload or calibration as fact without captured evidence or a cited manufacturer source. Use the classifications and [evidence ledger](../EVIDENCE.md). Website appearance does not confer technical verification.

## Links to code

The site renders files within `build-manual/`. For source code in the repository outside that folder, use full GitHub URLs rather than relative Markdown links.
