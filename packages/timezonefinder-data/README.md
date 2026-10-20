# timezonefinder-data

The timezone boundary data used by
[timezonefinder](https://github.com/jannikmi/timezonefinder), compiled from
[timezone-boundary-builder](https://github.com/evansiroky/timezone-boundary-builder)
releases into the binary format described in
[the data format reference](https://timezonefinder.readthedocs.io/en/latest/data_format.html).

`pip install timezonefinder` installs this package automatically - there is nothing
extra to do. It is a separate distribution so that a new boundary release can ship
without a `timezonefinder` release, and so that a deployment can pin the dataset its
answers came from:

```
pip install "timezonefinder-data==3.2026.3.post1"
```

The version reads `<format>.<year>.<letter>[.postN]`: the year and numbered letter
name the
timezone-boundary-builder release (`2026c` -> `2026.3`), and the major is the binary
data format generation. A `.postN` suffix identifies revised compiled data made from
the same upstream release. `timezonefinder` requires a data version inside the format
generation it can read, so an ordinary data update needs no code release while a
format change is refused by the resolver instead of at the first lookup.

## Releases

- `4.2026.5` - timezone-boundary-builder [2026e](https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026e), 2026-10-18 - Updated the packaged boundaries to upstream 2026e and introduced data format 4: a longitude/latitude-aligned grid tree of 0.75° cells, refined into 4×4 blocks where zones meet, replacing the H3 index. Where two zones overlap, the smaller zone now answers in every cell, rather than whichever zone the index cell's vertex counts put first; compared with `3.2026.4` that moves Kafia Kingi and Abyei from `Africa/Khartoum` to `Africa/Juba`, the West Bank overlap from `Asia/Jerusalem` to `Asia/Hebron`, the Southern Patagonian Ice Field from `America/Punta_Arenas` to `America/Argentina/Rio_Gallegos`, the Croatia-Serbia Danube border from `Europe/Belgrade` to `Europe/Zagreb`, the Bay of Piran from `Europe/Zagreb` to `Europe/Ljubljana`, a strip of the Strait of Juan de Fuca from `America/Los_Angeles` to `America/Vancouver`, and slivers of the Sint Maarten and Nova Scotia-New Brunswick borders from `America/Marigot` to `America/Lower_Princes` and from `America/Halifax` to `America/Moncton`. Upstream 2026e also extends `Europe/Madrid` over a strip of sea off the Cerbère-Portbou coast that `Europe/Paris` still covers, which now answers `Europe/Madrid`.
- `3.2026.4` - timezone-boundary-builder [2026d](https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026d), 2026-09-21 - Updated the packaged boundaries to upstream 2026d.
- `3.2026.3.post1` - timezone-boundary-builder [2026c](https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026c), 2026-09-10 - Recompiled shortcut candidates in estimated full-lookup work order.
- `3.2026.3` - timezone-boundary-builder [2026c](https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026c), 2026-09-02 - Introduced shortcut format 3 with conservative polygon-cell overlap coverage.
- `2.2026.3` - timezone-boundary-builder [2026c](https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026c), 2026-08-23 - Added latitude-block indexes and packed coordinate payloads.
- `1.2026.3` - timezone-boundary-builder [2026c](https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026c), 2026-08-18 - First standalone data distribution.

## License

The boundary data is licensed under the Open Database License (ODbL), see
[DATA_LICENSE](https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE). The `timezonefinder` source code is MIT licensed.
