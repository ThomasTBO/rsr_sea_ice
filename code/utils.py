import numpy as np
from pyproj import Transformer
import os
import pandas as pd
from scipy.spatial import cKDTree


def latlon_to_cartesian(lat, lon, radius=6371):
    # lat, lon in degrees
    lat = np.radians(lat)
    lon = np.radians(lon)
    x = radius * np.cos(lat) * np.cos(lon)
    y = radius * np.cos(lat) * np.sin(lon)
    z = radius * np.sin(lat)
    return np.stack((x, y, z), axis=-1)


def clean_csv(input_file):
    """Cleans the CSV file by removing unnecessary newlines and spaces.

    Args:
        input_file (str): Path to the input CSV file.
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
        for i in range(10):
            content = content.replace(str(i)+'\n', str(i)+' ').replace('.\n', '.0 ')
    with open(input_file.replace('.csv', '.csv'), 'w', encoding='utf-8') as f:
        f.write(content)


def arctic_grid(step_km=10, lat_min=72, **kwargs):
    """Create a grid of points in the Arctic region.

    Args:
        step_km (int, optional): The distance between grid points in kilometers. Defaults to 10.
        lat_min (float, optional): The minimum latitude for the grid (deg). Defaults to 72.

    Returns:
        np.ndarray: An array of shape (N, 2) containing the latitude and longitude of each grid point.
    """

    # Define the EPSG:3413 zone (in meters)
    x_min, x_max = -2500000, 2500000
    y_min, y_max = -2500000, 2500000
    step = step_km * 1000  # step in meters

    x_vals = np.arange(x_min, x_max + step, step)
    y_vals = np.arange(y_min, y_max + step, step)
    xx, yy = np.meshgrid(x_vals, y_vals)
    xy_grid = np.column_stack([xx.ravel(), yy.ravel()])

    # Inverse transformation to get lat/lon
    transformer = Transformer.from_crs("EPSG:3413", "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(xy_grid[:, 0], xy_grid[:, 1])
    latlon_grid = np.column_stack((lats, lons))

    # Filter to keep only points north of lat_min
    mask = latlon_grid[:, 0] >= lat_min
    latlon_grid = latlon_grid[mask]

    return latlon_grid  # shape (N, 2), columns: [lat, lon]


def read_psep_from_csv(path):
    """Read psep values from the CSV files generated during the extraction

    Args:
        path (str): Path to the CSV files.

    Returns:
        latlon_array (np.ndarray): Array of latitudes and longitudes.
        powers_2D_array (np.ndarray): 2D array of power values.
    """
    latlon_array = []
    powers_2D_array = []

    csv_files = [f for f in os.listdir(path) if f.endswith('.csv') and f.startswith('psep')]
    
    for i,csv_file in enumerate(csv_files):
        print(f"Reading data from {csv_file}, file {i+1}/{len(csv_files)}")
        data = pd.read_csv(os.path.join(path, csv_file))
        data_array = data[['lat', 'lon', 'psep']].values
        
        for (lat, lon, power_array) in data_array:
            latlon_array.append((float(lat), float(lon)))
            powers_2D_array.append(np.fromstring(power_array.strip('[]'), sep=' '))

    return np.array(latlon_array), np.array(powers_2D_array)


def create_dictionary_from_xyz(lst):
    """
    Create a dictionary from a list of tuples.
    Each tuple should contain three elements: (x, y, z).
    """
    return {(x, y, z): i for i, (x, y, z) in enumerate(lst)}


def is_ice(latlon_target, KD_tree):
    """Check if the target point is over ice, ie we have data, ie the closest point in KD tree is close enough (<10km)

    Args:
        latlon_target (tuple): Latitude and longitude of the target point.
        KD_tree (cKDTree): KD-tree containing ice coordinates.

    Returns:
        bool: True if the target point is over ice, False otherwise.
    """
    xyz_closest = find_closest_points(KD_tree, [latlon_target], k=1)
    xyz_closest = xyz_closest[0]
    xyz_target = latlon_to_cartesian(latlon_target[0], latlon_target[1])
    distance = np.linalg.norm(xyz_closest - xyz_target) # in km

    return distance < 10


def build_KDtree(points_latlon):
    """
    Build a KD-tree from the given points (in lat/lon format).
    
    Args:
        points_latlon (np.ndarray): An array of shape (N, 2) where N is the number of points in (latitude, longitude) format.

    Returns:
        cKDTree: A KD-tree constructed from the points.
        dict: A dictionary mapping (x, y, z) coordinates to their original indices.
    """
    
    print("Transforming lat/lon to Cartesian coordinates for KD-tree construction...")
    points_cartesian = latlon_to_cartesian(points_latlon[:, 0], points_latlon[:, 1])
    
    # Filter out inf or nan values
    print(f"Number of points before nan/inf filtering: {len(points_cartesian)}")
    points_cartesian = points_cartesian[~np.isnan(points_cartesian).any(axis=1)]
    points_cartesian = points_cartesian[~np.isinf(points_cartesian).any(axis=1)]
    print(f"Number of points after nan/inf filtering: {len(points_cartesian)}")
    
    print("Building KD-tree...")
    return cKDTree(points_cartesian), create_dictionary_from_xyz(points_cartesian)


def find_closest_points(tree, latlon_target_list, k=1000, **kwargs):
    """Find the closest points in the KD-tree for multiple target points.

    Args:
        tree (cKDTree): The KD-tree to search.
        latlon_target_list (list): A list of target points in (latitude, longitude) format.
        k (int, optional): The number of closest neighbors to find. Defaults to 1000.

    Returns:
        np.ndarray: An array of shape (M, k) with the indices of the k closest points for each target.
    """
    latlon_target_array = np.array(latlon_target_list)
    if latlon_target_array.ndim == 1:
        latlon_target_array = latlon_target_array.reshape(1, 2)
    points_cartesian = latlon_to_cartesian(latlon_target_array[:, 0], latlon_target_array[:, 1])
    _, indices = tree.query(points_cartesian, k=k)
    
    # tree.data[indices[i,j]] is the j-th closest point to the i-th target
    return tree.data[indices]

