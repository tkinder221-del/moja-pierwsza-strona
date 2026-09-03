# Extension compatibility status

| Capability | M1 status | Evidence |
| --- | --- | --- |
| Manifest V3 unpacked load | Pending runtime gate | Chromium Android extension browser tests + fixture |
| Content scripts | Pending runtime gate | BraveMvpFixtureContentScript + ContentScriptInjection |
| MV3 service worker | Pending runtime gate | ServiceWorkerBasedExtension |
| storage.local | Pending runtime gate | StorageApiTestStorageAreaLocal |
| runtime messaging | Pending runtime gate | MessagePassing |
| General CRX install | Not implemented | M2 |
| Mobile extension manager | Not implemented | M2 |
| Action popup UI | Not implemented | M3 |
| Chrome Web Store | Not implemented | M4 |

Statuses become `Proven` only after the corresponding Android x86 runtime tests pass on the same overlay commit used for the extension APK build.
