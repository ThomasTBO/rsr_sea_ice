import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap
import pandas as pd
import json
import os
from utils import read_psep_from_csv
from find_closest_KD import build_KDtree, find_closest_points_KDtree
import rsr


def virgin_aeqd_map(lon_0, width, height):
    m = Basemap(
        projection='npstere',
        lon_0=lon_0,
        boundinglat=65,
        width=width,
        height=height,
        resolution='i'
    )
    m.drawcoastlines(linewidth=1.0, color='black')
    m.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    return m


def plot_rsr_results(path_to_data, year, month, latlon_target_list=None, **kwargs):
    """Plot RSR results from all CSV files in the specified directory beginning with 'rsr_results_'.
    This function generates scatter plots for total power, incoherent power, coherent power, and correlation coefficient.
    If `latlon_target_list` is provided, it will also plot the distributions and HK model fits for these target points.

    Args:
        path_to_data (str): Path to the directory containing RSR results.
        year (str): Year of the data.
        month (str): Month of the data.
        latlon_target_list (list, optional): List of target latitude/longitude for distribution plotting. Defaults to None.
    """
    
    if latlon_target_list:
        plot_distributions(path_to_data, latlon_target_list, year, month, **kwargs)

    lat_array = []
    lon_array = []
    pt_array = []
    pn_array = []
    pc_array = []
    crl_array = []
    flag_array = []

    data_array = np.empty((0, 5))
    csv_files = [f for f in os.listdir(path_to_data) if f.startswith('rsr_results_') and f.endswith('.csv')]
    print(len(csv_files), "CSV files found in", path_to_data)
    for i, csv_file in enumerate(csv_files):
        print(f"Reading data from {csv_file}, file {i+1}/{len(csv_files)}")
        data = pd.read_csv(os.path.join(path_to_data, csv_file))
        if data_array.shape == (0,):
            data_array = data[['lat','lon','power','crl','flag']].values
        else:
            data_array = np.concatenate((data_array,data[['lat','lon','power','crl','flag']].values), axis=0)

    
    for (lat, lon, power, crl, flag) in data_array:
        lat_array.append(lat)
        lon_array.append(lon)
        pt_array.append(json.loads(power)["pt"])
        pn_array.append(json.loads(power)["pn"])
        pc_array.append(json.loads(power)["pc"])
        crl_array.append(crl)
        flag_array.append(flag)


    # Filter leads and flaged points   NOT LEADS EVENTULLY

    # lead_KD, dictionnary = create_lead_KDtree('./data/uit_cryosat2_L2_alongtrack_2018_02.csv')

    def flag_and_lead_filter(latlon,value,flag):
        if flag == 1 :  #and not(is_lead(latlon, lead_KD, dictionnary)):
            return value
        return np.nan

    pt_array = [flag_and_lead_filter((lat, lon), pt, flag) for (lat, lon), pt, flag in zip(zip(lat_array, lon_array), pt_array, flag_array)]
    pn_array = [flag_and_lead_filter((lat, lon), pn, flag) for (lat, lon), pn, flag in zip(zip(lat_array, lon_array), pn_array, flag_array)]
    pc_array = [flag_and_lead_filter((lat, lon), pc, flag) for (lat, lon), pc, flag in zip(zip(lat_array, lon_array), pc_array, flag_array)]
    crl_array = [flag_and_lead_filter((lat, lon), crl, flag) for (lat, lon), crl, flag in zip(zip(lat_array, lon_array), crl_array, flag_array)]


    # Create Basemap
    
    margin = 0 # degrés de marge autour des points
    s = 0.1  # taille des points

    lat_min = min(lat_array)-margin  # ne pas descendre sous 65°N
    lat_max = min(max(lat_array)+margin, 90)
    lon_min = min(lon_array)-margin
    lon_max = max(lon_array)+margin
    lat_moyen = 90
    lon_moyen = 0
    width = (lon_max - lon_min) * 15000  # en mètres
    height = 2* (lat_max - lat_min) * 130000  # en mètres

    
    m_pt = virgin_aeqd_map(lat_moyen, lon_moyen, width, height)
    m_pn = virgin_aeqd_map(lat_moyen, lon_moyen, width, height)
    m_pc = virgin_aeqd_map(lat_moyen, lon_moyen, width, height)
    m_crl = virgin_aeqd_map(lat_moyen, lon_moyen, width, height)

    plt.figure(figsize=(8,7))
    if latlon_target_list:
        lat_target_list = np.array([latlon[0] for latlon in latlon_target_list])
        lon_target_list = np.array([latlon[1] for latlon in latlon_target_list])
        x_dot, y_dot = m_pt(lon_target_list, lat_target_list)
        sc_dot = m_pt.scatter(x_dot, y_dot, c='red', s=10, zorder=10, label='Targets')
    x, y = m_pt(lon_array, lat_array)
    sc = m_pt.scatter(x, y, c=pt_array, cmap='viridis', s=s, zorder=5, vmin=38.5, vmax=40)
    m_pt.drawcoastlines(linewidth=1.0, color='black')
    m_pt.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    plt.colorbar(sc, label='pt (dB)')
    plt.title(f"Total power - {month} {year}")
    plt.savefig(path_to_data+"pt_distribution.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    plt.figure(figsize=(8,7))
    x, y = m_pn(lon_array, lat_array)
    sc = m_pn.scatter(x, y, c=pn_array, cmap='viridis', s=s, zorder=5, vmin=8, vmax=22)
    m_pn.drawcoastlines(linewidth=1.0, color='black')
    m_pn.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    plt.colorbar(sc, label='pn (dB)')
    plt.title(f"Incoherent power - {month} {year}")
    plt.savefig(path_to_data+"pn.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    plt.figure(figsize=(8,7))
    x, y = m_pc(lon_array, lat_array)
    sc = m_pc.scatter(x, y, c=pc_array, cmap='viridis', s=s, zorder=5, vmin=38.5, vmax=40.5)
    m_pc.drawcoastlines(linewidth=1.0, color='black')
    m_pc.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    plt.colorbar(sc, label='pc (dB)')
    plt.title(f"Coherent power - {month} {year}")
    plt.savefig(path_to_data+"pc.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    plt.figure(figsize=(8,7))
    x, y = m_crl(lon_array, lat_array)
    sc = m_crl.scatter(x, y, c=crl_array, cmap='viridis', s=s, zorder=5, vmin=0.5, vmax=1)
    m_crl.drawcoastlines(linewidth=1.0, color='black')
    m_crl.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    plt.colorbar(sc, label='crl')
    plt.title(f"Correlation coefficient - {month} {year}")
    plt.savefig(path_to_data+"crl.png", dpi=300, bbox_inches='tight')
    plt.close()
    

    print("Plots saved in ", path_to_data)


def plot_distributions(path, latlon_target_list, year, month, nb_closest=1000):
    """Plot the power distributions for targets, as well as the HK model fits.

    Args:
        path (str): Path to the directory containing RSR results.
        latlon_target_list (list): List of target latitude/longitude pairs.
        year (str): Year of the data.
        month (str): Month of the data.
        nb_closest (int): Number of closest points to consider for each target. (e.g. if you indicate 1000, there will be 64000 psep values in input of the rsr, as each burst is composed of 64 echoes)
    """
    
    # Find the 1000 closest psep
    
    latlon_array, powers_2D_array = read_psep_from_csv(os.path.join(path, "psep"))
    
    KD_tree, dictionary = build_KDtree(latlon_array)
    
    powers_list = []
    
    for latlon_target in latlon_target_list:
        xyz_closest = find_closest_points_KDtree(KD_tree, latlon_target, k=nb_closest)
        indices_closest = [dictionary[tuple(point)] for point in xyz_closest]
        powers_for_rsr = powers_2D_array[indices_closest]
        powers_for_rsr = powers_for_rsr.flatten() 
        powers_list.append(powers_for_rsr)

    
    # Apply rsr

    f_list = [rsr.run.processor(powers, fit_model='hk', min_method='least_squares') for powers in powers_list]
    pw_range_list = [(min(powers), max(powers)) for powers in powers_list]
    pdf_list = [rsr.pdf.hk(f.values, np.linspace(min_p, max_p, 1000)) for f, (min_p, max_p) in zip(f_list, pw_range_list)]
    
    
    # Save the pdf values in a csv

    with open(os.path.join(path, 'HK_parameters.csv'), 'w') as f:
        f.write("lat,lon,pdf.values,pdf.crl,pdf.powers\n")
        for (lat,lon), f in zip(latlon_target_list, f_list):
            f.write(f"{lat},{lon},{f.values},{f.crl()},{f.powers()}\n")


    # Plot the power distribution

    for i in range(len(latlon_target_list)):
        latlon_target = latlon_target_list[i]
        powers = powers_list[i]
        f = f_list[i]
        pw_range = np.linspace(pw_range_list[i][0], pw_range_list[i][1], 1000)
        
        plt.figure(figsize=(8, 6))
        plt.hist(powers, bins=100, alpha=0.7, density=True)
        plt.plot(pw_range, pdf_list[i], 'r-', lw=2, label='HK PDF')
        plt.title(f'Power Distribution and HK model at {latlon_target} for {month}/{year}')
        plt.xlabel('Power')
        plt.ylabel('Probability Density')
        plt.grid(True)
        plt.legend()
        plt.savefig(os.path.join(path, f'power_distribution_{round(latlon_target[0])}_{round(latlon_target[1])}.png'), dpi=300, bbox_inches='tight')
        plt.close()


