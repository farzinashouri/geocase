"""Catalog errors."""

from __future__ import annotations

from geocase.catalog.manifests import build_manifest_uri, resolve_manifest_case
from geocase.catalog.models import ManifestMetadata


class RemoteCaseUnavailableError(KeyError):
    """A case id is catalogued in a manifest, but its data is not local.

    Subclasses :class:`KeyError` on purpose: ``registry.get()`` has always
    raised ``KeyError`` for an id it cannot return, and code that catches
    ``KeyError`` keeps working when a manifest is added to the registry.

    Attributes:
        case_id: The requested case id.
        manifest_key: The manifest that lists it.
        uri: Where the artifact is published, when the manifest says.
    """

    def __init__(
        self,
        message: str,
        *,
        case_id: str,
        manifest_key: str,
        uri: str | None = None,
    ) -> None:
        super().__init__(message)
        self.case_id = case_id
        self.manifest_key = manifest_key
        self.uri = uri

    def __str__(self) -> str:
        # ``KeyError.__str__`` reprs its argument, which would wrap the whole
        # message in quotes and escape it. The message is the point here.
        return str(self.args[0])


def remote_case_unavailable(
    case_id: str,
    manifest: ManifestMetadata,
) -> RemoteCaseUnavailableError:
    """Build the error for a manifest-backed case that cannot be loaded."""
    uri: str | None
    try:
        entry = resolve_manifest_case(manifest, case_id)
    except KeyError:
        uri = None
    else:
        uri = build_manifest_uri(manifest, entry)

    location = f" It is published at {uri}." if uri else ""
    return RemoteCaseUnavailableError(
        f"Case '{case_id}' is listed in manifest '{manifest.manifest_key}', "
        f"whose data is not bundled with GeoCase, and this release does not "
        f"fetch remote data (planned for v1.1).{location} "
        f"Run `pytest -m 'not remote'` to skip cases like it, or see "
        f"docs/remote-datasets.md.",
        case_id=case_id,
        manifest_key=manifest.manifest_key,
        uri=uri,
    )
