# Creating a Ruby repository

A Ruby repository is an HTTPS-hosted JSON index pointing to `.springys` archives. Ruby's Mac.APK bridge reads the index, downloads packages, checks their SHA-256 hashes and validates their contents before showing them in Ruby. Users can browse, search, install, update and remove supported packages. This is beta functionality and has not been fully verified end-to-end in Spring.

V1 `.springys` packages select existing WinterX hooks. V2 distributes independently authored JavaScript using WinterX's documented API, requiring a compatible running engine. Start with [Making `.springys` packages](springys-format.md). Rooted Android and a LAN bridge are not supported yet.

## 1. Build and inspect a package

From your WinterX checkout, use your own package folder and choose a new output filename:

```sh
mkdir -p /tmp/my-ruby-repo/packages
python3 tools/springys_tool.py build my-first-tweak /tmp/my-ruby-repo/packages/my-first-tweak-1.0.0.springys
python3 tools/springys_tool.py inspect /tmp/my-ruby-repo/packages/my-first-tweak-1.0.0.springys
shasum -a 256 /tmp/my-ruby-repo/packages/my-first-tweak-1.0.0.springys
```

Copy the 64 lowercase hexadecimal characters printed by `shasum`; do not include the filename. The same hash also appears in the inspector output. Validate each package before publishing.

## 2. Create your index

Create `/tmp/my-ruby-repo/index.json`. Replace the hash placeholder below with the **actual hash** of the archive you just built:

```json
{
  "format": "winterx.repository/1",
  "name": "Example's Ruby Repository",
  "packages": [
    {
      "url": "packages/my-first-tweak-1.0.0.springys",
      "sha256": "REPLACE_WITH_64_LOWERCASE_HEX_CHARACTERS"
    }
  ]
}
```

Your files should look like this:

```text
my-ruby-repo/
├── index.json
└── packages/
    └── my-first-tweak-1.0.0.springys
```

Add more entries to the `packages` array for other packages. Put a comma between entries, not after the last one. The index contains archive URLs and hashes; Ruby reads names, descriptions, authors, icons and preview images from each package's manifest. You don't add those fields to the index.

## 3. Host the files over HTTPS

Upload `index.json` and `packages/` to a public static HTTPS host, preserving the directory structure. For example, if the index is published at `https://example.com/ruby/index.json`, the relative URL above resolves to `https://example.com/ruby/packages/my-first-tweak-1.0.0.springys`. Both URLs must return the actual files, not an HTML sign-in page. GitHub Pages or another static host can be used; publishing a GitHub repository by itself does not automatically provide a working static-site URL.

Before sharing the source, open the HTTPS index and package URL in a browser or use `curl` to confirm they are public. Never use credentials or URL fragments in the source URL. HTTP is rejected; HTTPS redirects must stay HTTPS.

## 4. Add and use the source in Ruby

1. Jailbreak Spring with a compatible WinterX build and keep the Ruby bridge running.
2. In Ruby, open the **Sources** tab, choose **Add Source…**, enter the full HTTPS URL of `index.json`, and tap **Add Source**.
3. Return to **Sources** and use **Refresh Sources**. Open **Packages → Browse Repositories** or use **Search** to find the package.
4. Open the package to see its description, author, version and available previews, then tap **Install**. Supported hook and engine requirements still apply.
5. To remove a source, tap its entry under **Sources**, then choose **Remove**. Removing a source does not automatically uninstall its installed packages; remove those from their package details.

A package enabled outside the registry may need manual removal before its package equivalent can be installed. V2 installs/updates stage code and need a deliberate full launcher reopen; the installer never automatically restarts Spring. Disabled, updated or uninstalled contexts are closed by their owning worker. State/data remain for recovery.

## 5. Publish an update

1. Keep the package ID the same, increment its manifest version, and build a new archive with a new filename.
2. Inspect the new archive and compute its SHA-256.
3. Upload the new archive, then update its index entry to point to the new filename and hash. Publishing the archive first reduces broken links while updating.
4. Ask users to select **Sources → Refresh Sources**. On the package's repository detail page, Ruby can offer **Update** when the installed archive hash differs.

The registry identifies a package by ID; update availability compares hashes, not semantic version ordering. Preserve the package ID and avoid offering the same ID for unrelated packages. Refresh may download all indexed archives, so keep archives small and hosting reliable.

## Index reference and limits

| Field | Rule |
| --- | --- |
| `format` | Exactly `winterx.repository/1`. |
| `name` | String from 1 to 80 characters. |
| `packages` | Array of up to 100 entries; an empty array is valid. |
| `packages[].url` | Relative to the index URL or an absolute HTTPS URL. |
| `packages[].sha256` | Exactly 64 lowercase hexadecimal characters matching the downloaded archive. |

The index is limited to 512 KiB. Each downloaded archive is limited to 12 MiB and is also subject to the [package format limits](springys-format.md#artwork-and-archive-limits). Ruby currently permits up to 50 user-added sources. It downloads and checks packages during refresh; a source can show an error while other valid entries remain available.

## Troubleshooting

- **Invalid source URL:** use the complete public `https://` index URL without a username, password, or fragment.
- **Unsupported repository format:** check the `format` string, JSON syntax and that the URL returns JSON rather than an HTML page.
- **Package checksum mismatch:** rebuild or re-download the exact archive being served and recompute its SHA-256. Update the index after uploading the archive; caches may briefly serve an older copy.
- **Package missing from the catalogue:** check the source's error in Ruby, the resolved package URL, its hash, and `python3 tools/springys_tool.py inspect package.springys`. A broken entry can coexist with valid ones.
- **Package won't install:** v1 requires its compiled hook; v2 requires the runtime in the checksum-verified running engine. A newer APK sitting on disk is not sufficient. Check the bridge terminal for the error.
- **Changes not showing:** refresh sources, then return to the package list. Confirm the index and archive served over HTTPS are the new files.

A hash detects mismatched content; it does not authenticate the publisher or guarantee safety. Only add sources/authors you trust, especially for executable tweaks. The local [`builtin-repo/`](../builtin-repo/) and [hosted copy](https://github.com/UltraFEmotes/Ruby-Repo) contain **Animaper and ColoredBar**, not developer/test examples.
