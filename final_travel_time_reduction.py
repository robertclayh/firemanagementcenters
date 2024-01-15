
import osmnx as ox
import geopandas as gpd
import pandas as pd
import networkx as nx
from tqdm import tqdm
import numpy as np

def calculate_travel_time(G, orig_node, dest_node):
    try:
        route = nx.shortest_path(G, orig_node, dest_node, weight='travel_time')
        travel_time = sum(G[u][v][0]['travel_time'] for u, v in zip(route[:-1], route[1:])) / 60  # in minutes
    except nx.NetworkXNoPath:
        travel_time = float('inf')
    return travel_time

def main():
    # Load datasets
    localities = gpd.read_file('Tlaxcala_localities.geojson')
    fire_risk_points = gpd.read_file('filtered_points_within_tlaxcala.geojson')

    # Filter localities with population over 10,000
    localities = localities[localities['POBTOT'] > 10000]

    # Filter high-risk points
    high_risk_points = fire_risk_points[fire_risk_points['gridcode'] == 5]

    # Load road network
    G = ox.graph_from_place('Tlaxcala, Mexico', network_type='drive')
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    # Prepare DataFrame for results
    results = pd.DataFrame()

    # Calculate travel time reductions for each locality
    for locality in tqdm(localities.itertuples(), total=localities.shape[0], desc="Processing localities"):
        orig_node = ox.nearest_nodes(G, locality.geometry.x, locality.geometry.y)
        new_travel_times = [calculate_travel_time(G, orig_node, ox.nearest_nodes(G, point.geometry.x, point.geometry.y)) 
                            for point in tqdm(high_risk_points.itertuples(), total=high_risk_points.shape[0], desc="Calculating travel times")]
        total_reduction = sum(current - new for current, new in zip(high_risk_points['travel_time'], new_travel_times) if new < current)
        average_reduction = total_reduction / len(new_travel_times) if len(new_travel_times) > 0 else 0
        
        new_row = pd.DataFrame({'locality': [getattr(locality, 'CODE')], 'total_reduction': [total_reduction], 'average_reduction': [average_reduction]})
        results = pd.concat([results, new_row], ignore_index=True)

    results = results.merge(localities, left_on='locality', right_on='CODE', how='left')
    results.to_csv('localities_travel_time_reduction.csv', index=False)

    print(f"Analysis completed. Results saved to 'localities_travel_time_reduction.csv'.")

if __name__ == "__main__":
    main()
