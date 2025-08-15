from extract_psep import extract_psep
from apply_rsr import apply_rsr_arctic
from plot_rsr_results import plot_rsr_results

if __name__ == "__main__":
    """
    Main entry point for the script.

    Recommend running this script in three times :
    1. First, run it to extract the PSEP (Peak Surface Echo Power)
    2. Then, run it to apply rsr
    3. Plot the results
    """
    
    year = "2018"
    month = "01"
    
    path = "./Cryosat_RSR_SAR_FBR_" + year + "_" + month        # To change as you like

    # Step 1 : Extract PSEP
    # /!\ Make sure you downloaded the txt file required before running (cf ReadMe)
    extract_psep(path, year, month)
    
    # Step 2 : Apply RSR
    # /!\ Make sure you dowloaded the rsr package AND applied the modifications by launching the script rsr_package_modification.py
    apply_rsr_arctic(path)

    # Step 3 : Plot the results
    plot_rsr_results(path, year, month, latlon_target_list=None)  # You can provide a list of target lat/lon pairs to plot their distributions