# Store Families

Store Families describe intended OpenGWASDB analytical products. Each family owns its Manifest Generator, accepted Release Manifests, Build Recipes, validation records, Store Releases, and Release Errata.

Use `_candidates/` for proposed Store Families that are still being assessed and have not yet received a permanent Store Family ID.

Within an accepted Store Family, `releases/<family-release-id>/` may contain candidate release bundles once they have a Family Release ID. Unreviewed generator output should stay outside the curated `releases/` tree.
