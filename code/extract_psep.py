import numpy as np
from netCDF4 import Dataset
from lead_filter import create_lead_KDtree, lead_SeaIce_mask
from concurrent.futures import ProcessPoolExecutor
import os
from utils import clean_csv
from download_ftp import find_nc_files_to_read, download_nc_files, delete_nc_files


def extract_psep(path, year, month, nb_files_per_batch=50, **kwargs):
    """
    Extracts the PSEP (Peak Surface Echo Power) from each echo available in the ftp
    server for the specified year and month, in the SAR FBR product.
    
    Stores the computed PSEP in several output csv files
    (latitude, longitude, powers[64])

    Requirement : The uit_cryosat2_L2_alongtrack_year_month.csv file must be in the repository.

    For some reason, the PSEP extraction happened to fail some times (computation stopping without any error message).
    If it happens, just relaunch the extraction : this function will not compute again or delete the PSEP already extracted.

    Args:
        path (str): The path to the work directory.
        year (str): The year of the products to process. (e.g. "2018")
        month (str): The month of the products to process. (e.g. "01")
        nb_files_per_batch (int): Number of files to process per batch. All the results from a batch will be stored in a single csv file. Defaults to 50.
    """
    
    # Build KDTree for lead filter
    csv_file_path = os.path.join(path, f"uit_cryosat2_L2_alongtrack_{year}_{month}.csv")
    if not os.path.exists(csv_file_path):
        txt_file_path = os.path.join(path, f"uit_cryosat2_L2_alongtrack_{year}_{month}.txt")
        if not os.path.exists(txt_file_path):
            raise FileNotFoundError(f"Required TXT file not found: {txt_file_path}\n You can download it from this link : https://uitno.app.box.com/s/37uuevawit4a6r8arkvmvty7o76tiqx1/folder/228797883958")
        else :
            os.rename(txt_file_path, csv_file_path)
    lead_SeaIce_KDtree, lead_SeaIce_dictionary = create_lead_KDtree(csv_file_path)
    
    
    # Create nc_files_to_read.txt if not already in the repository
    nc_files_to_read_path = os.path.join(path, "nc_files_to_read.txt")
    if not os.path.exists(nc_files_to_read_path):
        find_nc_files_to_read(path, year, month, **kwargs)


    # Read nc_files_to_read.txt
    with open(nc_files_to_read_path, 'r') as f:
        nc_files = f.readlines()
    nc_files = [line.strip() for line in nc_files if line.strip()]
    nb_files = len(nc_files)   


    # Extract PSEP from batches if not already done
    psep_dir = os.path.join(path, "psep")
    os.makedirs(psep_dir, exist_ok=True)
    
    for i in range(0, nb_files, nb_files_per_batch):
        batch_files = nc_files[i:min(i + nb_files_per_batch, nb_files)]
        output_filename = os.path.join(psep_dir, f"psep_{year}_{month}_{i}_{i + len(batch_files)}.csv")
        if (not os.path.exists(output_filename)) or os.path.getsize(output_filename) < 10000 :
            extract_psep_batch(year, month, path, batch_files, lead_SeaIce_KDtree, lead_SeaIce_dictionary, i, **kwargs)
    

def extract_psep_batch(year, month, path, filenames, lead_SeaIce_KDtree, lead_SeaIce_dictionary, index_first_file, **kwargs):
    """
    Extracts the PSEP from a batch of NetCDF files.

    Args:
        year (str): The year of the products to process. (e.g. "2018")
        month (str): The month of the products to process. (e.g. "01")
        path (str): The path to the directory we work in.
        filenames (list): List of NetCDF filenames to process.
        lead_SeaIce_KDtree (cKDTree): KDTree for lead/sea ice detection.
        lead_SeaIce_dictionary (dict): Dictionary for lead/sea ice information.
        index_first_file (int): The index of the first file in the batch.
    """
    
    # Create a directory for the NetCDF files
    nc_dir = os.path.join(path, f"{index_first_file}_{index_first_file + len(filenames)}")
    os.makedirs(nc_dir, exist_ok=True)

    download_nc_files(nc_dir, year, month, filenames, **kwargs)

    output_filename = os.path.join(path, f"psep/psep_{year}_{month}_{index_first_file}_{index_first_file + len(filenames)}.csv")

    with open(output_filename, 'w') as csvfile:
        csvfile.write('lat,lon,psep\n')
        for i,filename in enumerate(filenames):
            print(f'Processing file {i+1}/{len(filenames)} : {filename}')
            with Dataset(os.path.join(nc_dir, filename), 'r') as nc:
                lat_data = nc.variables['lat_85_ku'][:]
                lon_data = nc.variables['lon_85_ku'][:]
            power_max_2D_vector = extract_psep_file(os.path.join(nc_dir, filename), lead_SeaIce_KDtree, lead_SeaIce_dictionary, **kwargs)
            for burst in range(power_max_2D_vector.shape[0]):
                if power_max_2D_vector[burst, 0] != 0:
                    csvfile.write(f'{lat_data[burst]},{lon_data[burst]},{power_max_2D_vector[burst, :]}\n')            
            
    delete_nc_files(nc_dir, year, month, filenames)
    
    # Clean the csv file
    clean_csv(output_filename)


def extract_psep_file(filename, lead_SeaIce_KDtree, lead_SeaIce_dictionary, nb_workers=8, **kwargs):
    """Extract PSEP from a single NetCDF file.

    Args:
        filename (str): Path to the NetCDF file.
        lead_SeaIce_KDtree (KDTree): KDTree for lead/sea ice detection.
        lead_SeaIce_dictionary (dict): Dictionary for lead/sea ice information.
        nb_workers (int, optional): Number of worker processes. Defaults to 8.

    Returns:
        np.ndarray: Array of extracted PSEP values.
    """

    # Open the NetCDF file and read the necessary variables
    with Dataset(filename, 'r') as nc:
        lat_data = nc.variables['lat_85_ku'][:]
        lon_data = nc.variables['lon_85_ku'][:]
    nb_bursts = len(lat_data)
    
    
    # Filter out the bursts that are leads and those with lat < lat_min (default = 72)
    latlon_bursts_to_filter = [(lat_data[burst], lon_data[burst], burst) for burst in range(nb_bursts)]
    bursts_filtered = filter_bursts(latlon_bursts_to_filter, lead_SeaIce_KDtree, lead_SeaIce_dictionary, **kwargs)
    nb_bursts_filtered = len(bursts_filtered)
    print(f"Number of bursts to process: {nb_bursts_filtered}/{nb_bursts}")

    # Process remaining bursts
    power_max_2D_vector = np.zeros((nb_bursts, 64))

    with ProcessPoolExecutor(max_workers=nb_workers) as executor:
        futures = [executor.submit(extract_psep_burst, burst, nb_bursts_filtered, filename, **kwargs) for burst in bursts_filtered]
    for future in futures:
        burst, local_power = future.result()
        power_max_2D_vector[burst, :] = local_power

    return power_max_2D_vector
    
    
def filter_bursts(latlon_burst_list, lead_SeaIce_KDtree, lead_SeaIce_dictionary, lat_min=72, **kwargs):
    """Filters the bursts based on latitude and lead information.

    Args:
        latlon_burst_list (list): List containing (latitude, longitude, burst index)
        lead_SeaIce_KDtree (KDTree): KDTree containing all the points for which we know if it is a lead and/or sea ice
            The points are in cartesian xyz coordinates.
        lead_SeaIce_dictionary (dict): Dictionary mapping cartesian coordinates to lead/Sea ice information for each
            point in the KDtree
        lat_min (float): Minimum latitude for filtering

    Returns:
        np.ndarray: Array containing the filtered burst indices.
    """
    print("Filtering bursts...")

    burst_array = np.array([burst for (lat, lon, burst) in latlon_burst_list])
    latlon_array = np.array([(lat, lon) for (lat, lon, burst) in latlon_burst_list])

    # Apply the latitude filter
    mask_step1 = latlon_array[:, 0] > lat_min
    burst_filtered_step1 = burst_array[mask_step1]
    latlon_filtered_step1 = latlon_array[mask_step1]
    if len(burst_filtered_step1) == 0:
        return []

    # Apply the lead and sea ice filter
    mask_step2 = lead_SeaIce_mask(latlon_filtered_step1, lead_SeaIce_KDtree, lead_SeaIce_dictionary)
    bursts_filtered_step2 = burst_filtered_step1[mask_step2]

    return bursts_filtered_step2


def extract_psep_burst(burst, nb_bursts, filename, **kwargs):
    """Extracts the PSEP (Peak Surface Echo Power) for a specific burst of 64 echoes.

    Args:
        burst (int): The index of the burst to process.
        nb_bursts (int): The total number of bursts to process.
        filename (str): The path to the NetCDF file containing the burst data.

    Returns:
        tuple: A tuple containing the burst index and the array of the extracted PSEP values.
    """

    if burst%1000 == 0:
        print(f"Processing burst {burst}/{nb_bursts}")

    with Dataset(filename, 'r') as nc:
        i_data = nc.variables['cplx_waveform_ch1_i_85_ku'][burst]
        q_data = nc.variables['cplx_waveform_ch1_q_85_ku'][burst]
        tot_gain_ch1_85_ku = nc.variables['tot_gain_ch1_85_ku'][burst]
        agc_1_85_ku = nc.variables['agc_1_85_ku'][burst]
        agc_2_85_ku = nc.variables['agc_2_85_ku'][burst]
        instr_cor_gain_tx_rx_85_ku = nc.variables['instr_cor_gain_tx_rx_85_ku'][burst]

    # Compute the total Gain
    static_gain = tot_gain_ch1_85_ku
    dynamic_gain = agc_1_85_ku + agc_2_85_ku + instr_cor_gain_tx_rx_85_ku
    total_gain = static_gain + dynamic_gain

    # Compute and store the PSEP for each one of the 64 echoes
    psep_burst = np.zeros(64)    
    for pulse in range(64):
        cplx_signal = i_data[pulse, :] + 1j * q_data[pulse, :]
        psep_echo = extract_psep_echo(cplx_signal, total_gain, **kwargs)
        if np.isfinite(psep_echo):
            psep_burst[pulse] = psep_echo
        else :
            return np.zeros(64)  # Return an array of zeros if the PSEP extraction fails

    return burst, psep_burst


def extract_psep_echo(complex_echo, gain, window_frac_psep=0.05, **kwargs):
    """Extracts the PSEP (Peak Surface Echo Power) from the complex echo signal.

    Args:
        complex_echo (np.ndarray): The input complex echo signal.
        gain (float): The gain to apply for calibration.
        window_frac_psep (float, optional): The fraction of the window size to use for max power extraction. Defaults to 0.05.

    Returns:
        float: The calibrated PSEP value.
    """

    # Perform FFT for range compression
    waveform = np.fft.fft(complex_echo)
    waveform = np.fft.fftshift(waveform)
    waveform = (np.abs(waveform)**2)/len(complex_echo)

    # Compute the leading edge index
    leading_edge_index = leading_edge(waveform, **kwargs)
    
    # Compute the max amplitude in the following window
    window_size = int(window_frac_psep * len(waveform))
    psep_index = np.argmax(waveform[leading_edge_index:leading_edge_index+window_size]) + leading_edge_index
    psep_count = waveform[psep_index]

    # Convert to dB and apply calibration
    psep_db = 10 * np.log10(psep_count)
    psep_db_calibrated = psep_db + gain
    
    return psep_db_calibrated


def leading_edge(waveform, window_frac_leading_edge=[0.03,0.06,0.09], **kwargs):
    """Compute the leading edge of a waveform signal.
    
    The leading edge is defined as the position of the maximum integrated echo amplitude gradient 

    Args:
        waveform (np.ndarray): The input waveform signal.
        window_frac (list, optional): The fractions of the window sizes used to compute the slopes. Defaults to [0.03,0.06,0.09].

    Returns:
        int: The index of the leading edge.
    """

    window_sizes = [int(wf * len(waveform)) for wf in window_frac_leading_edge]

    slopes = []
    for i in range(len(waveform) - max(window_sizes)):
        slope=[]
        for window_size in window_sizes:
            segment = waveform[i:i+window_size]
            slope.append(np.mean(np.gradient(segment)))
        slopes.append(slope)

    mean_slopes = np.mean(slopes, axis=1)
    leading_edge_index = np.argmax(mean_slopes)
    return leading_edge_index