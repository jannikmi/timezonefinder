# Twitter as Data (Steinert-Threlkeld, 2018)

- **BibTeX key:** `steinertthrelkeld2018twitter`
- **Venue:** Cambridge Elements (Quantitative and Computational Methods for the Social Sciences), Cambridge University Press, 2018
- **DOI:** [10.1017/9781108529327](https://doi.org/10.1017/9781108529327)
- **Field:** computational social science methods (textbook)
- **Verification:** full text read on 2026-11-19, in the author-hosted copy of the Cambridge Core PDF (<https://zacharyst.com/wp-content/uploads/2018/09/twitter_as_data_final.pdf>, 52 pages, Cambridge Core download stamp of 16 February 2018). One mention, in a code listing in Section 3.4, "Converting to Local Time" (printed page 43, PDF page 47).

## How timezonefinder is referenced

The section explains that Twitter's `created_at` field is in Greenwich Mean Time and that "if the tweet contains GPS coordinates, the local time it was created is known with certainty. With precise location information, you can identify the timezone of the tweet and adjust accordingly." The listing that follows contains:

```text
# Get timezones
tf = TimezoneFinder()
zone = tf.timezone_at(lng=longitude, lat=latitude)
# Gives string of name of timezone
timezone = pytz.timezone(zone) # Convert string to pytz format
```

Cited as: code only. The listing names the class `TimezoneFinder` and its method `timezone_at`, but the prose names neither the package nor its import, and the book has no reference entry for it. The full script the listing excerpts is linked as www.cambridge.org/download_file/949173, which refused a download from here (HTTP 403).

## Role of timezonefinder

Converts tweet timestamps from UTC to the author's local time. The longitude and latitude are the south-west corner of the tweet's place bounding box, the package returns the zone name, and `pytz` converts the timestamp. Tweets without coordinates fall back to the `utc_offset` of the user's profile.

## Notes

- A methods textbook with 152 Scholar citations. The mention is a worked code example, so the book teaches the package to a social-science audience.
- Ties with the CMAS abstract as the earliest publication found.
