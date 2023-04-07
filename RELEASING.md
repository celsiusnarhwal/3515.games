# Releasing

1. Run `kurisu check` and fix anything it complains about.

2. Make sure the [`Dockerfile`](Dockerfile) builds and runs correctly.

3. Run `kurisu licenses`.

4. Commit any uncommitted changes to `dev`.

5. Merge `dev` into `main` via pull request.

   ```bash
   gh pr create --label privileged
   ```

6. Place 3515.games in maintenance mode.

7. Publish a new release.

   ```bash
   poe release --publish
   ```
