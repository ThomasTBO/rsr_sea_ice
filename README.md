# rsr_sea_ice

## Overview
The purpose of this project is to apply the  Radar Statistical Reconnaissance (RSR) technique over Arctic sea ice, to get the spatial distribution of the Coherent and Non Coherent Power (Pc and Pn).

The data used is the Cryosat-2 Synthetic Aperture Radar (SAR) Full Bit Rate (FBR) product.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)
- [Example](#example)
- [Contact](#contact)


## Installation

```bash
git clone https://github.com/yourusername/rsr_sea_ice.git
cd rsr_sea_ice
pip install -r requirements.txt
python rsr_package_modification.py
```

## Usage

- In main.py, Change the ```year```, ```month``` and ```path``` paramaters as you wish. You can also comment some of the steps if you don't want to launch all of them at once.
- Download and put in your working repository (the one you chose for ```path```) the .txt file with the right month and year, available here : https://uitno.app.box.com/s/37uuevawit4a6r8arkvmvty7o76tiqx1/folder/228797883958.
- Launch the computation : ```python main.py```

I sometimes faced some issues computing the first step. If for any reason the computing stops before the end of the process, you can just launch again this step : the powers already extracted will not be erased or computed again. 


## Documentation

### extract_psep

```python 
extract_psep(path, year, month, nb_files_per_batch=50, nb_workers=8, lat_min=72, window_frac_psep=0.05, window_frac_leading_edge=[0.03,0.06,0.09], username='anonymous', password='anonymous@anonymous.com', port=21, ftp_server='science-pds.cryosat.esa.int')
```
Extracts the PSEP (Peak Surface Echo Power) from each echo available in the ftp
server for the specified year and month, in the SAR FBR product.

Stores the computed PSEP in several output csv files
(latitude, longitude, powers[64])

Requirement : The uit_cryosat2_L2_alongtrack_year_month.csv file must be in the repository.

#### Arguments :

- ```path``` (str): The path to the work directory
- ```year``` (str): The year of the products to process. (e.g. "2018")
- ```month``` (str): The month of the products to process. (e.g. "01")

#### Optional arguments :

- ```nb_files_per_batch``` (int): Number of files to process per batch. All the results from a batch will be stored in a single csv file. Defaults to 50.
- ```nb_workers``` (int): Number of worker processes. Defaults to 8.
- ```lat_min``` (float): Minimum latitude for filtering (deg). Defaults to 72.0
- ```window_frac_psep``` (float): The fraction of the window size to use for max power extraction. Defaults to 5%.
- ```window_frac_leading_edge``` (float list): The fractions of the window sizes used to compute the slopes. Defaults to [0.03,0.06,0.09].
- ```user``` (str): The username for FTP authentication. Defaults to 'anonymous'.
- ```password``` (str): The password for FTP authentication. Defaults to 'anonymous@anonymous.com'
- ```port``` (int): The port number for the FTP server. Defaults to 21
- ```ftp_server``` (str): The address of the FTP server. Defaults to 'science-pds.cryosat.esa.int'


### apply_rsr_arctic

```python 
apply_rsr_arctic(path, nb_cores=8, nb_closest=1000, step_km=10, lat_min=72.)
```
Apply RSR to the Arctic grid and save the results in CSV files.

#### Arguments :

- ```path``` (str): The path to the work directory

#### Optional arguments :

- ```nb_cores``` (int): Number of worker processes. Defaults to 8.
- ```nb_closest``` (int): Number of closest points to consider for each target. (e.g. if you indicate 1000, there will be 64000 psep values in input of the rsr, as each burst is composed of 64 echoes). Defaults to 1000
- ```step_km``` (int): The distance between grid points in kilometers. Defaults to 10.
- ```lat_min``` (float): Minimum latitude for filtering (deg). Defaults to 72.0


### plot_rsr_results

```python 
plot_rsr_results(path_to_data, year, month, latlon_target_list=None, nb_closest=1000)
```
Plot RSR results from all CSV files in the specified directory beginning with 'rsr_results_'.
This function generates scatter plots for total power, incoherent power, coherent power, and correlation coefficient.
If `latlon_target_list` is provided, it will also plot the distributions and HK model fits for these target points.


#### Arguments :

- ```path_to_data``` (str): Path to the directory containing RSR results.
- ```year``` (str): Year of the data.
- ```month``` (str): Month of the data.

#### Optional arguments :

- ```latlon_target_list``` (list): List of target latitude/longitude for distribution plotting. Defaults to None.
- ```nb_closest``` (int): Number of closest points to consider for each target. (e.g. if you indicate 1000, there will be 64000 psep values in input of the rsr, as each burst is composed of 64 echoes). Defaults to 1000


## Example

In the example repository of this project, you can find the results I got by applying this code to the Nov 2017 Cryosat-2 data : the csv files with the rsr results (output of step 2) and some figures (output of step 3)

## Contact

Author : Thomas Thébault, Aug 2025
Mail : thomas.thebault@student.isae-supaero.fr