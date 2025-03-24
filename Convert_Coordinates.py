import os
import pandas as pd
from pyproj import Transformer

root = r'./dir'
read_fn = "Point_sampled.csv"  # Your File Name
df = pd.read_csv(os.path.join(root, read_fn))

# EPSG:3857
transformer = Transformer.from_crs("origin", "EPSG:3857", always_xy=True)        # use WGS84

lon, lat = transformer.transform(df["X"].values, df["Y"].values)


df_new = pd.DataFrame({
    "FID": range(len(df)),  
    "Join_Count": 0,
    "TARGET_FID": 0,
    "Id": 0,
    "osm_id": 0,
    "code": 0,
    "fclass": "residential", 
    "name": "",
    "ref": "",
    "oneway": "B",
    "maxspeed": 0,
    "layer": 0,
    "bridge": "F",
    "tunnel": "F",
    "pid": 1,
    "Lon": lon,
    "Lat": lat
})

output_path = "converted_data.csv"
df_new.to_csv(output_path, index=False)

print(f"Completed! Saved at {output_path}")