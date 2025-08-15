from scipy.spatial import cKDTree
from utils import latlon_to_cartesian
import pandas as pd


def create_lead_KDtree(filename):
    """Create a KD-tree from lead coordinates in a CSV file.

    Args:
        filename (str): The path to the CSV file containing lead coordinates.

    Returns:
        tuple: A tuple containing the KD-tree and a dictionary mapping coordinates to lead and sea ice classes.
    """
    
    print("Creating KD-tree for lead coordinates...")
    
    data = pd.read_csv(filename)
    coords_and_leadclass = data[[' Latitude', ' Longitude',' Lead_Class', ' Sea_Ice_Class']].values
    
    lead_coords = []
    lead_class_list = []
    sea_ice_class_list = []
    for (lat, lon, lead_class, sea_ice_class) in coords_and_leadclass:
        if(lat>=72.0):
            lead_coords.append(latlon_to_cartesian(lat, lon))
            lead_class_list.append(lead_class)
            sea_ice_class_list.append(sea_ice_class)

    dictionary = { tuple(coord) : (lead_class, sea_ice_class) for coord, lead_class, sea_ice_class in zip(lead_coords, lead_class_list, sea_ice_class_list) }

    return cKDTree(lead_coords), dictionary


def lead_SeaIce_mask(points_latlon, lead_SeaIce_KDtree, lead_SeaIce_dictionary):
    """
    Compute the mask for lead and sea ice points.

    Args:
        points_latlon (list): A list of tuples containing (latitude, longitude) coordinates.
        lead_SeaIce_KDtree (cKDTree): The KD-tree containing lead coordinates.
        lead_SeaIce_dictionary (dict): A dictionary mapping coordinates to lead and sea ice classes.

    Returns:
        list: A list of bool masking the (not(lead) and Sea Ice) 
            (True if not a lead and is sea ice).
    """
    points_xyz = [latlon_to_cartesian(lat, lon) for lat, lon in points_latlon]
    _, indices = lead_SeaIce_KDtree.query(points_xyz, k=1)
    return [lead_SeaIce_dictionary[tuple(lead_SeaIce_KDtree.data[idx])] == (0,1) for idx in indices]
