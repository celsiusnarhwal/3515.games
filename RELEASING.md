# Releasing

1. Run `kurisu check` and fix anything it complains about.

2. Update the announcement banner in [`docs/main.html`](docs/main.html) accordingly.

3. Make sure the [`Dockerfile`](Dockerfile) builds and runs correctly.

4. Run `kurisu licenses`.

5. Commit any uncommitted changes to `dev`.

6. Merge `dev` into `main` via pull request.

   ```bash
   gh pr create --label privileged
   ```

7. Place 3515.games in maintenance mode.

8. Publish a new release.

   ```bash
   poe release --publish
   ```
