"""
Batch processing example: answering many coordinates in one call.

``timezone_ids_at`` / ``timezone_names_at`` take one array per axis and answer the whole
batch at once, which hoists the validation and the shortcut lookup out of the per-point
loop. Prefer the id form whenever the names are not the end product: mapping ids back to
names costs one Python string per coordinate, which is most of what a batch avoids.

The scalar ``timezone_at`` remains the right call for a single point.
"""

from timezonefinder import NO_ZONE_ID, TimezoneFinder


def main():
    # Create the instance once and reuse it - initialisation dominates a single lookup
    tf = TimezoneFinder(in_memory=True)

    lngs = [13.358, 2.3522, -74.0060, 139.6917, -43.1729, 151.2093, 0.0]
    lats = [52.5061, 48.8566, 40.7128, 35.6895, -22.9068, -33.8688, 0.0]

    print("One call for the whole batch:")
    print("=" * 60)
    for lng, lat, name in zip(lngs, lats, tf.timezone_names_at(lngs=lngs, lats=lats)):
        print(f"({lng:9.4f}, {lat:9.4f}) -> {name}")

    print("\nIds instead of names, for a caller that maps them itself:")
    zone_ids = tf.timezone_ids_at(lngs=lngs, lats=lats)
    print(f"  {zone_ids} (dtype {zone_ids.dtype})")

    print("\nA batch with an unanswerable coordinate in it:")
    spoilt_lngs = [13.358, 999.0, 2.3522]
    spoilt_lats = [52.5061, 0.0, 48.8566]
    # the default is on_invalid="raise", matching the scalar methods. "skip" answers the
    # rest rather than discarding the work done for them.
    names = tf.timezone_names_at(lngs=spoilt_lngs, lats=spoilt_lats, on_invalid="skip")
    ids = tf.timezone_ids_at(lngs=spoilt_lngs, lats=spoilt_lats, on_invalid="skip")
    print(f"  names: {names}")
    print(f"  ids:   {ids} ({NO_ZONE_ID} stands where a scalar lookup answers None)")

    print("\n✓ Processed every coordinate with one call per array")


if __name__ == "__main__":
    main()
