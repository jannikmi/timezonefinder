from timezonefinder import TimezoneFinder

tf = TimezoneFinder()

# Example using timezone name
geometry_name = tf.get_geometry(tz_name="Africa/Addis_Ababa", coords_as_pairs=True)
print(f"Geometry for Africa/Addis_Ababa:\n{geometry_name}")

# Example using timezone ID (optional)
geometry_id = tf.get_geometry(tz_id=400, use_id=True)
print(f"Geometry for timezone ID 400:\n{geometry_id}")
