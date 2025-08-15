from scipy.spatial import cKDTree
import numpy as np
from utils import create_dictionary_from_xyz, latlon_to_cartesian


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


def find_closest_points(tree, latlon_target_list, k=1000):
    """Find the closest points in the KD-tree for multiple target points.

    Args:
        tree (cKDTree): The KD-tree to search.
        latlon_target_list (list): A list of target points in (latitude, longitude) format.
        k (int, optional): The number of closest neighbors to find. Defaults to 1000.

    Returns:
        np.ndarray: An array of shape (M, k) with the indices of the k closest points for each target.
    """
    latlon_target_array = np.array(latlon_target_list)
    points_cartesian = latlon_to_cartesian(latlon_target_array[:, 0], latlon_target_array[:, 1])
    _, indices = tree.query(points_cartesian, k=k)
    
    # tree.data[indices[i,j]] is the j-th closest point to the i-th target
    return tree.data[indices]

