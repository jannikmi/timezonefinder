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
pip install "timezonefinder-data==2.2026.3"
```

The version reads `<format>.<year>.<letter>`: the trailing two parts name the
timezone-boundary-builder release (`2026c` -> `2026.3`), and the major is the binary
data format generation. `timezonefinder` requires a data version inside the format
generation it can read, so an ordinary data update needs no code release while a
format change is refused by the resolver instead of at the first lookup.

## Releases

- `2.2026.3` - timezone-boundary-builder [2026c](https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026c), 2026-08-23
- `1.2026.3` - timezone-boundary-builder [2026c](https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026c), 2026-08-18

## License

The boundary data is licensed under the Open Database License (ODbL), see
[DATA_LICENSE](https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE). The `timezonefinder` source code is MIT licensed.
