# Water management in agriculture and a global crop-evapotranspiration forecasting tool (Pandey, 2025)

- **BibTeX key:** `pandey2025water`
- **Venue:** M.S. thesis, Oklahoma State University, 2025 (adviser Jeffrey Sadler; ProQuest Dissertations & Theses 32164368)
- **URL:** <https://search.proquest.com/openview/c92c595f0e71fe096bfa3fe2d35519e2/1>; open PDF in the university repository, linked from Google Scholar: <https://openresearch.okstate.edu/bitstreams/e882a0d8-574a-45db-8933-cc5eb4916341/download>
- **Field:** agricultural water management
- **Verification:** full text read (repository PDF); mentioned in Sect. 3.3.5 "Cloud Computing Architecture for ETc Forecasts", p. 36, and in the code of Appendix C (the AWS Lambda script, also published as `Okstate-WaDE/et_forecast_lambda` on GitHub). The bibliography has no entry for it.

## How timezonefinder is referenced

> The data processing includes the following: i) Time zone detection: The time zone corresponding to the user's location is identified using the timezonefinder module. ii) Time conversion: After detecting the time zone, image timestamp (originally in UTC) is converted to local timezone using the zoneinfo module.

Appendix C shows the call:

```python
from timezonefinder import TimezoneFinder

...
tf = TimezoneFinder()
timezone_str = tf.timezone_at(lng=longitude, lat=latitude)
if timezone_str:
    local_timezone = ZoneInfo(timezone_str)
```

Cited as: named inline and in code. No reference-list entry, URL or version.

## Role of timezonefinder

A cloud service (AWS Lambda) produces crop-evapotranspiration forecasts for users of the Canopeo app anywhere in the world. For each request it looks up the zone of the user's field from its coordinates and converts the UTC timestamps of the planting date and the canopy photo to local time before the forecast is generated.

## Notes

- A deployed service rather than a one-off analysis: every forecast request runs the lookup. A commented-out earlier version of the same block in the appendix used `pytz`; the shipped version uses `zoneinfo`.
