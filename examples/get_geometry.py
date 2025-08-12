from timezonefinder import TimezoneFinder

tf = TimezoneFinder()

# Example using timezone name
timezone_name = "Europe/Paris"
geometry_by_name = tf.get_geometry(tz_name=timezone_name, coords_as_pairs=True)
print(f"Geometry for timezone '{timezone_name}':\n{geometry_by_name}")

# Example using timezone ID
timezone_id = 12
geometry_by_id = tf.get_geometry(tz_id=timezone_id, use_id=True)
print(f"Geometry for timezone ID {timezone_id}:\n{geometry_by_id}")
