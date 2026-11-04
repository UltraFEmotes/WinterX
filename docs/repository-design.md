# Creating a Ruby repository

Ruby repositories are HTTPS-hosted JSON indexes of `.springys` packages. Ruby's Mac.APK bridge downloads each package, verifies its SHA-256 and validates its manifest before displaying it. Ruby can browse, search and show the package's icon, description and previews. Installing, updating and removing a package uses the local package registry. These features are in development and have not yet been verified end-to-end in Spring.

## 1. Build a package

Follow [the package guide](springys-format.md). Only hooks already implemented by the installed WinterX engine can currently be installed. A package cannot add arbitrary new behavior merely by declaring a new hook.

## 2. Create an index

```json
{
  "format": "winterx.repository/1",
  "name": "Example Repository",
  "packages": [
    {
      "url": "packages/my-tweak.springys",
      "sha256": "REPLACE_WITH_THE_64_CHARACTER_SHA256"
    }
  ]
}
```

Compute the hash with `shasum -a 256 packages/my-tweak.springys`. Put the lowercase hash in the index. Ruby resolves relative package URLs against the index URL; absolute HTTPS URLs also work. Package metadata and artwork come from the package itself. Publish the index and archives on HTTPS, then enter the full index URL under **Packages → Sources → Add Source**. When a package changes, publish the new archive and update its hash, then use **Refresh Sources** in Ruby. The index supports up to 100 packages; packages are currently downloaded during refresh.

A minimal development repository is in [`builtin-repo/`](../builtin-repo/). It is not yet the user's hosted built-in repository.

## Safety and compatibility

Each archive is limited to 12 MB compressed and is checked against the index hash and package format. The hash protects against accidental corruption and mismatches; it does not establish trust in a repository or its author. Only add repositories you trust. This version does not execute scripts or native code in downloaded archives. Rooted Android and LAN bridge support are not available yet.
