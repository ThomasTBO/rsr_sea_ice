from utils import arctic_grid,read_psep_from_csv, is_ice, build_KDtree, find_closest_points
from concurrent.futures import ProcessPoolExecutor
import csv
import json
import rsr
import os

def apply_rsr_arctic(path, **kwargs):
    """
    Apply RSR to the Arctic grid and save the results in CSV files.

    Args:
        path (str): Path to the data directory.
        **kwargs: Additional keyword arguments for apply_rsr and arctic_grid.
    """
    
    print("Generating Arctic grid...")
    latlon_target_array = arctic_grid(**kwargs)
    
    print("Reading PSEP data from CSV files...")
    latlon_array, powers_2D_array = read_psep_from_csv(os.path.join(path, "psep"))

    print("Applying RSR to Arctic grid...")
    apply_rsr(latlon_target_array, latlon_array, powers_2D_array, path, **kwargs)
    

def apply_rsr(latlon_target_array, latlon_array, powers_2D_array, path, nb_cores=8, **kwargs):
    """Apply RSR to each target and save the results in csv files.

    Args:
        latlon_target_array (np.ndarray): Array of target latitudes and longitudes.
        latlon_array (np.ndarray): Array of input latitudes and longitudes.
        powers_2D_array (np.ndarray): 2D array of input psep values.
        path (str): Path to the data directory.
        nb_cores (int): Number of CPU cores to use for processing.
    """
    
    print("Building KD-tree for lat/lon coordinates...")
    KD_tree, _ = build_KDtree(latlon_array)

    latlon_target_array_filtered = [latlon_target for latlon_target in latlon_target_array if is_ice(latlon_target, KD_tree)]
    print(f"Number of target points over ice: {len(latlon_target_array_filtered)} / {len(latlon_target_array)}")
    
    latlon_target_array_filtered = latlon_target_array_filtered[0:30]

    # Split the filtered target points among the available cores
    nb_target_per_core = len(latlon_target_array_filtered) // nb_cores
    futures = []
    with ProcessPoolExecutor(max_workers=nb_cores) as executor:
        futures = [executor.submit(apply_rsr_core, latlon_target_array_filtered[i*nb_target_per_core:((i + 1)*nb_target_per_core if i!=nb_cores-1 else len(latlon_target_array_filtered))], latlon_array, powers_2D_array, path, i, **kwargs) for i in range(nb_cores)]

    print("RSR processing completed and results saved.")
    

def apply_rsr_core(latlon_target_array,  latlon_array, powers_2D_array, path_to_data, core_id, **kwargs):
    """Applies RSR to the given target points.

    Args:
        latlon_target_array (np.ndarray): Array of target latitudes and longitudes.
        latlon_array (np.ndarray): Array of input latitudes and longitudes.
        powers_2D_array (np.ndarray): 2D array of input psep values.
        path_to_data (str): Path to the data directory.
        core_id (int): ID of the core processing the batch.
    """

    print(f"Core {core_id}: Building KD-tree for lat/lon coordinates...")
    KD_tree, dictionary = build_KDtree(latlon_array)
    
    # Process apply_rsr_multi_targets with 1000 target points each time
    
    results = []

    # Number of batches of targets
    nb_calls = len(latlon_target_array) // 1000 + 1 if len(latlon_target_array) % 1000 != 0 else len(latlon_target_array) // 1000
    
    for i in range(nb_calls):
        latlon_target_batch = latlon_target_array[i*1000:min((i+1)*1000, len(latlon_target_array))]
        results.extend(apply_rsr_batch(latlon_target_batch, KD_tree, dictionary, powers_2D_array,core_id,i,len(latlon_target_array), **kwargs))



    print(f"Core {core_id}: Saving RSR results in csv")
    with open(os.path.join(path_to_data, 'rsr_results_core_'+str(core_id)+'.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['lat', 'lon', 'value', 'power', 'crl', 'flag'])
        for (latlon_target, f) in results:
            value_str = json.dumps(f.values)
            power_str = json.dumps(f.power())
            crl_str = json.dumps(f.crl())
            flag_str = json.dumps(f.flag())
            writer.writerow([latlon_target[0], latlon_target[1], value_str, power_str, crl_str, flag_str])

    print(f"Core {core_id}: RSR processing completed and results saved.")
    
    
def apply_rsr_batch(latlon_target_array, KD_tree, dictionary, powers_2D_array, core_id, index, nb_targets_core, nb_closest=1000, min_method='leastsq'):
    """Apply RSR to a batch of target points.

    Args:
        latlon_target_array (np.ndarray): Array of target latitudes and longitudes.
        KD_tree (cKDTree): KD-tree containing psep measures coordinates.
        dictionary (dict): Dictionary mapping coordinates to indices.
        powers_2D_array (np.ndarray): 2D array of psep values.
        core_id (int): ID of the core processing the batch.
        index (int): Index of the batch.
        nb_targets_core (int): Total number of targets for the core.
        nb_closest (int): Number of closest points to consider for each target. (e.g. if you indicate 1000, there will be 64000 psep values in input of the rsr, as each burst is composed of 64 echoes)
        min_method (str): Minimization method used in the lmfit HK-fitting. Defaults to 'leastsq'.

    Returns:
        list: List of tuples containing target coordinates and RSR results.
    """
    
    print(f"Core {core_id}: Processing targets {index*1000+1} to {index*1000+len(latlon_target_array)} / {nb_targets_core}")
    xyz_closest_array = find_closest_points(KD_tree, latlon_target_array,k=nb_closest)

    f_array = []

    for i, xyz_closest in enumerate(xyz_closest_array):
        if i % 10 == 0:
            print(f"Core {core_id}: Processing target {index*1000+i+1}/{nb_targets_core}")
        # Process each set of closest points for the target
        indices_closest = [dictionary[tuple(point)] for point in xyz_closest]
        powers_for_rsr = powers_2D_array[indices_closest]
        powers_for_rsr = powers_for_rsr.flatten()
        f = rsr.run.processor(powers_for_rsr, fit_model='hk', min_method=min_method)
        f_array.append(f)

    return list(zip(latlon_target_array, f_array))