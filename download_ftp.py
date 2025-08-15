from ftplib import FTP
import os
import xml.etree.ElementTree as ET


def find_nc_files_to_read(path,year,month,lat_min=72, username='anonymous', password='anonymous@anonymous.com', port=21, ftp_server='science-pds.cryosat.esa.int'):
    """
    Downloads the header files from the SAR FBR Cryosat-2 products, 
    and write in a txt file the name of the NetCDF files to read.
    
    Those NetCDF files are selected if the track of the satellite
    contains measures above lat_min.

    When it's done, deletes all the downloaded header files.

    Args:
        path (str): The path to the directory where the header files are stored.
        year (int): The year of the products to process.
        month (int): The month of the products to process.
        lat_min (float, optional): The minimum latitude to consider. Defaults to 72.
        user (str): The username for FTP authentication. Defaults to 'anonymous'.
        password (str): The password for FTP authentication. Defaults to 'anonymous@anonymous.com'.
        port (int): The port number for the FTP server. Defaults to 21.
        ftp_server (str): The address of the FTP server. Defaults to 'science-pds.cryosat.esa.int'.
    """
    
    ftp = FTP()
    ftp.connect(ftp_server, port=port)
    ftp.login(username, password)
    ftp.cwd(f'/SIR_SAR_FR/{year}/{month}/')
    available_files = set(ftp.nlst())

    filtered_nc_filenames = []
    
    print(f"Processing headers for {year}-{month}...")

    for i, filename in enumerate(available_files):
        if filename.endswith('.HDR'):
            with open(path+filename, 'wb') as local_file:
                ftp.retrbinary(f'RETR {filename}', local_file.write)
            try:
                tree = ET.parse(path+filename)
                root = tree.getroot()
                prod_loc = root.find('.//Product_Location')
                if prod_loc is not None:
                    start_lat = float(prod_loc.find('Start_Lat').text) / 1e6
                    stop_lat = float(prod_loc.find('Stop_Lat').text) / 1e6
                    if start_lat > lat_min or stop_lat > lat_min:
                        filtered_nc_filenames.append(filename.replace('.HDR', '.nc'))
                    os.remove(path + filename)  # Remove the header file after checking
                else :
                    print(f"Product_Location not found in {filename}. Skipping.")
            except Exception as e:
                print(f"Error parsing {filename}: {e}")

    # Write the filtered NetCDF filenames to a text file
    with open(os.path.join(path, 'nc_files_to_read.txt'), 'w') as f:
        f.writelines(filtered_nc_filenames)

    # Close the FTP connection
    ftp.quit()


def download_nc_files(path, year, month, filenames, username='anonymous', password='anonymous@anonymous.com', port=21, ftp_server='science-pds.cryosat.esa.int'):
    """
    Downloads the NetCDF files for the specified year and month in the given range,
    in a new repository.

    Args:
        path (str): The path to the directory where the txt file to read is stored.
        year (int): The year of the products to process.
        month (int): The month of the products to process.
        filenames (list): The list of NetCDF filenames to download.
        user (str): The username for FTP authentication.
        password (str): The password for FTP authentication.
        port (int): The port number for the FTP server.
        ftp_server (str): The address of the FTP server.
    """
    
    ftp = FTP()
    ftp.connect(ftp_server, port=port)
    ftp.login(username, password)
    ftp.cwd(f'/SIR_SAR_FR/{year}/{month}/')
    available_files = set(ftp.nlst())
    

    for i, filename in enumerate(filenames):
        if i%10 == 0:
            print(f"{i}/{len(filenames)} files downloaded")
        filename = filename.strip()
        if filename in available_files:
            with open(path+filename, 'wb') as local_file:
                ftp.retrbinary(f'RETR {filename}', local_file.write)
        else:
            print(f"file {filename} not found on FTP server.")

    print(f"All files downloaded to {path}.")

    # Close the FTP connection
    ftp.quit()
    

def delete_nc_files(path, year, month, filenames):
    """
    Deletes the NetCDF files for the specified year and month in the given range, and the repository

    Args:
        path (str): The path to the directory where the NetCDF files are stored.
        year (int): The year of the products to process.
        month (int): The month of the products to process.
        filenames (list): The list of NetCDF filenames to delete.
    """

    for filename in filenames:
        file_path = os.path.join(path, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            print(f"File not found for deletion: {file_path}")

    if not os.listdir(path):
        os.rmdir(path)
    else :
       print(f"Directory not empty for deletion: {path}")

