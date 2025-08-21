import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap
import pandas as pd
import json
import os
from utils import read_psep_from_csv, build_KDtree, find_closest_points
import rsr
import matplotlib.patches as mpatches


def virgin_aeqd_map(lon_0, width, height):
    m = Basemap(
        projection='npstere',
        lon_0=lon_0,
        boundinglat=65,
        resolution='i'
    )
    m.drawcoastlines(linewidth=1.0, color='black')
    m.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    return m


def plot_rsr_results(path_to_data, year, month, latlon_target_list=None, blurry=False, min_crl=0., **kwargs):
    """Plot RSR results from all CSV files in the specified directory beginning with 'rsr_results_'.
    This function generates scatter plots for total power, incoherent power, coherent power, and correlation coefficient.
    If `latlon_target_list` is provided, it will also plot the distributions and HK model fits for these target points.

    Args:
        path_to_data (str): Path to the directory containing RSR results.
        year (str): Year of the data.
        month (str): Month of the data.
        latlon_target_list (list, optional): List of target latitude/longitude for distribution plotting. Defaults to None.
        blurry (bool, optional): Whether to apply a blur to the plots (increasing the point size and lessening the opacity). Defaults to False.
        min_crl (float, optional): Minimum CRL value for filtering points. Defaults to 0.
    """
    
    if latlon_target_list:
        plot_distributions(path_to_data, latlon_target_list, year, month, **kwargs)

    print("Plotting RSR results on heat maps")

    lat_array = []
    lon_array = []
    pt_array = []
    pn_array = []
    pc_array = []
    pcpn_array = []
    crl_array = []
    flag_array = []

    # Read data

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
        pcpn_array.append(json.loads(power)["pc-pn"])
        crl_array.append(crl)
        flag_array.append(flag)


    # Filter out flagged targets and too low crl

    pt_array = [pt for pt, flag, crl in zip(pt_array, flag_array, crl_array) if (crl >= min_crl and flag==1)]
    pn_array = [pn for pn, flag, crl in zip(pn_array, flag_array, crl_array) if (crl >= min_crl and flag==1)]
    pc_array = [pc for pc, flag, crl in zip(pc_array, flag_array, crl_array) if (crl >= min_crl and flag==1)]
    pcpn_array = [pcpn for pcpn, flag, crl in zip(pcpn_array, flag_array, crl_array) if (crl >= min_crl and flag==1)]
    lat_array = [lat for lat, crl, flag in zip(lat_array, crl_array, flag_array) if (crl >= min_crl and flag==1)]
    lon_array = [lon for lon, crl, flag in zip(lon_array, crl_array, flag_array) if (crl >= min_crl and flag==1)]
    crl_array = [crl for crl, flag in zip(crl_array, flag_array) if (crl >= min_crl and flag==1)]


    # Create Basemap
    
    margin = 0
    if blurry:
        s = 50  # point size
        alpha = 0.1  # point opacity
        blurred_mention = "_blurred"
    else :
        s = 0.1  # point size
        alpha = 1  # point opacity
        blurred_mention = ""

    lat_min = min(lat_array)-margin
    lat_max = min(max(lat_array)+margin, 90)
    lon_min = min(lon_array)-margin
    lon_max = max(lon_array)+margin
    lat_avg = 90
    lon_avg = 0
    width = (lon_max - lon_min) * 15000
    height = 2* (lat_max - lat_min) * 130000

    
    m_pt = virgin_aeqd_map(lon_avg, width, height)
    m_pn = virgin_aeqd_map(lon_avg, width, height)
    m_pc = virgin_aeqd_map(lon_avg, width, height)
    m_pcpn = virgin_aeqd_map(lon_avg, width, height)
    m_crl = virgin_aeqd_map(lon_avg, width, height)

    plt.figure(figsize=(8,7))
    distributions_mention = ""
    if latlon_target_list:
        lat_target_list = np.array([latlon[0] for latlon in latlon_target_list])
        lon_target_list = np.array([latlon[1] for latlon in latlon_target_list])
        x_dot, y_dot = m_pt(lon_target_list, lat_target_list)
        sc_dot = m_pt.scatter(x_dot, y_dot, c='red', s=10, zorder=10, label='Targets')
        distributions_mention = "_with_targets"
    x, y = m_pt(lon_array, lat_array)
    sc = m_pt.scatter(x, y, c=pt_array, cmap='viridis', s=s, zorder=5, vmin=38.5, vmax=40, alpha=alpha)
    m_pt.drawcoastlines(linewidth=1.0, color='black')
    m_pt.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    plt.colorbar(sc, label='pt (dB)')
    plt.title(f"Total power - {month} {year}")
    plt.savefig(os.path.join(path_to_data, "pt"+distributions_mention+blurred_mention+".png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    plt.figure(figsize=(8,7))
    x, y = m_pn(lon_array, lat_array)
    sc = m_pn.scatter(x, y, c=pn_array, cmap='viridis', s=s, zorder=5, vmin=8, vmax=22, alpha=alpha)
    m_pn.drawcoastlines(linewidth=1.0, color='black')
    m_pn.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    plt.colorbar(sc, label='pn (dB)')
    plt.title(f"Incoherent power - {month} {year}")
    plt.savefig(os.path.join(path_to_data, "pn"+blurred_mention+".png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    plt.figure(figsize=(8,7))
    x, y = m_pc(lon_array, lat_array)
    sc = m_pc.scatter(x, y, c=pc_array, cmap='viridis', s=s, zorder=5, vmin=38.5, vmax=40.5, alpha=alpha)
    m_pc.drawcoastlines(linewidth=1.0, color='black')
    m_pc.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    plt.colorbar(sc, label='pc (dB)')
    plt.title(f"Coherent power - {month} {year}")
    plt.savefig(os.path.join(path_to_data, "pc"+blurred_mention+".png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    plt.figure(figsize=(8,7))
    x, y = m_pcpn(lon_array, lat_array)
    sc = m_pcpn.scatter(x, y, c=pcpn_array, cmap='viridis', s=s, zorder=5, vmin=38.5, vmax=40.5, alpha=alpha)
    m_pcpn.drawcoastlines(linewidth=1.0, color='black')
    m_pcpn.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)
    plt.colorbar(sc, label='Pc/Pn (dB)')
    plt.title(f"Power ratio - {month} {year}")
    plt.savefig(os.path.join(path_to_data, "pcpn"+blurred_mention+".png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    
    plt.figure(figsize=(8,7))
    x, y = m_crl(lon_array, lat_array)
    
    crl_colors = []
    for crl in crl_array:
        if 0.99 <= crl <= 1:
            crl_colors.append('#1a9850')      # vert foncé
        elif 0.98 <= crl < 0.99:
            crl_colors.append('#66bd63')      # vert clair
        elif 0.96 <= crl < 0.98:
            crl_colors.append('#fee08b')      # jaune
        elif 0.90 <= crl < 0.96:
            crl_colors.append('#fdae61')      # orange
        else:  # crl < 0.9
            crl_colors.append("#000000")      # rouge foncé

    sc = m_crl.scatter(x, y, c=crl_colors, s=s, zorder=5, alpha=alpha)
    m_crl.drawcoastlines(linewidth=1.0, color='black')
    m_crl.fillcontinents(color='gray', lake_color='aqua', alpha=0.5)

    legend_patches = [
        mpatches.Patch(color='#1a9850', label='0.99 ≤ crl ≤ 1'),
        mpatches.Patch(color='#66bd63', label='0.98 ≤ crl < 0.99'),
        mpatches.Patch(color='#fee08b', label='0.96 ≤ crl < 0.98'),
        mpatches.Patch(color='#fdae61', label='0.90 ≤ crl < 0.96'),
        mpatches.Patch(color="#000000", label='crl < 0.90'),
    ]
    plt.legend(handles=legend_patches, loc='lower left', title='Correlation coefficient')
    plt.title(f"Correlation coefficient - {month} {year}")
    plt.savefig(os.path.join(path_to_data, "crl"+blurred_mention+".png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    print("Plots saved in ", path_to_data)


def plot_distributions(path, latlon_target_list, year, month, nb_closest=1000, min_method='least_squares', **kwargs):
    """Plot the power distributions for targets, as well as the HK model fits.

    Args:
        path (str): Path to the directory containing RSR results.
        latlon_target_list (list): List of target latitude/longitude pairs.
        year (str): Year of the data.
        month (str): Month of the data.
        nb_closest (int): Number of closest points to consider for each target. (e.g. if you indicate 1000, there will be 64000 psep values in input of the rsr, as each burst is composed of 64 echoes)
        min_method (str): Minimization method used in the lmfit HK-fitting. Defaults to 'least_squares'.
    """
    
    # Find the 1000 closest psep
    
    latlon_array, powers_2D_array = read_psep_from_csv(os.path.join(path, "psep"))
    
    KD_tree, dictionary = build_KDtree(latlon_array)
    
    powers_list = []
    
    for latlon_target in latlon_target_list:
        xyz_closest = find_closest_points(KD_tree, latlon_target, k=nb_closest)
        xyz_closest = xyz_closest[0]  # If only one target, we get a single array instead of a list of arrays
        indices_closest = [dictionary[tuple(point)] for point in xyz_closest]
        powers_for_rsr = powers_2D_array[indices_closest]
        powers_for_rsr = powers_for_rsr.flatten() 
        powers_list.append(powers_for_rsr)

    
    # Apply rsr

    f_list = [rsr.run.processor(powers, fit_model='hk', min_method=min_method) for powers in powers_list]
    pw_range_list = [(min(powers), max(powers)) for powers in powers_list]
    pdf_list = [rsr.pdf.hk(f.values, np.linspace(min_p, max_p, 1000)) for f, (min_p, max_p) in zip(f_list, pw_range_list)]
    
    
    # Save the pdf values in a csv
    
    path = os.path.join(path, "distributions")
    os.makedirs(path, exist_ok=True)

    with open(os.path.join(path, 'HK_parameters.csv'), 'w') as file:
        file.write("lat,lon,pdf.values,pdf.crl,pdf.powers\n")
        for (lat,lon), f in zip(latlon_target_list, f_list):
            file.write(f"{lat},{lon},{f.values},{f.crl()},{f.power()}\n")


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


