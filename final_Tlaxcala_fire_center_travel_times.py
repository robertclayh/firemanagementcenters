import os
import geopandas as gpd
import pandas as pd
import numpy as np
import networkx as nx
from shapely.geometry import Point
import osmnx as ox
from tqdm import tqdm

def get_state_boundary(state_name):
    return ox.geocode_to_gdf(f'{state_name}, Mexico')

# Fetch boundary for Tlaxcala
print("Fetching boundary for Tlaxcala...")
tlaxcala_boundary = get_state_boundary("Tlaxcala")
tlaxcala_bbox = tlaxcala_boundary.total_bounds

# Load the road network data for Tlaxcala using OSMnx
print("Loading road network data for Tlaxcala using OSMnx...")
G_proj = ox.graph_from_bbox(tlaxcala_bbox[3], tlaxcala_bbox[1], tlaxcala_bbox[2], tlaxcala_bbox[0], network_type='drive')
print("Loaded road network for Tlaxcala.")

# Add edge speeds and travel times
G_proj = ox.speed.add_edge_speeds(G_proj)
G_proj = ox.speed.add_edge_travel_times(G_proj)

# Define grid points
print("Defining grid points...")
resolution = 1 / 111  # 1 km grid
lat_points = np.arange(tlaxcala_bbox[1], tlaxcala_bbox[3], resolution)
lon_points = np.arange(tlaxcala_bbox[0], tlaxcala_bbox[2], resolution)
grid_points = [(lat, lon) for lat in lat_points for lon in lon_points]

# Fire management center coordinates for Tlaxcala
fire_center_coord = (19.313986266256705, -98.38758533896876)
orig_node = ox.nearest_nodes(G_proj, fire_center_coord[1], fire_center_coord[0])

# Calculate travel times from the fire center to each grid point with a progress bar
travel_times = []
for point in tqdm(grid_points, desc="Calculating travel times"):
    dest_node = ox.nearest_nodes(G_proj, point[1], point[0])
    try:
        route = nx.shortest_path(G_proj, orig_node, dest_node, weight='travel_time')
        travel_time = sum(G_proj[u][v][0]['travel_time'] for u, v in zip(route[:-1], route[1:])) / 60  # in minutes
    except nx.NetworkXNoPath:
        travel_time = float('inf')
    travel_times.append({'geometry': Point(point[1], point[0]), 'travel_time': travel_time})

# Create GeoDataFrame from the results
gdf = gpd.GeoDataFrame(travel_times, crs='EPSG:4326')

# Export to GeoJSON (Point file)
point_output_filename = 'fire_center_travel_times_tlaxcala_api.geojson'
gdf.to_file(point_output_filename, driver='GeoJSON')

print(f"Point data exported to {point_output_filename}")
