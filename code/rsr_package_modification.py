import importlib.util
import os

old_block_run_1 = "def processor(amp, gain=0., bins='stone', fit_model='hk', scaling=True, **kwargs):\n    \"\"\"Apply RSR over a sample of amplitudes"
new_block_run_1 = "def processor(amp, gain=0., bins='stone', fit_model='hk', scaling=True, min_method='leastsq', **kwargs):\n    \"\"\"Apply RSR over a sample of amplitudes\n\n    Warning: This function has been modified from the original C.Grima implementation"

old_block_run_2 = "    a = fit.lmfit( np.abs(amp), bins=bins, fit_model=fit_model)"
new_block_run_2 = "    a = fit.lmfit( np.abs(amp), bins=bins, fit_model=fit_model, min_method=min_method)"

old_block_fit_1 = "def lmfit(sample, fit_model='hk', bins='auto', p0 = None,\n          xtol=1e-4, ftol=1e-4):\n    \"\"\"Lmfit"
new_block_fit_1 = "def lmfit(sample, fit_model='hk', bins='auto', p0 = None,\n          xtol=1e-4, ftol=1e-4, min_method='leastsq'):\n    \"\"\"Lmfit\n    \n    Warning: This function has been modified from the original C.Grima implementation"

old_block_fit_2 = "    # use 'lbfgs' fit if error with 'leastsq' fit\n    try:\n        p = minimize(pdf2use, prm0, args=(x, n), method='leastsq',\n            xtol=xtol, ftol=ftol)\n    except KeyboardInterrupt:\n        raise\n    except:\n        # TODO: do we expect a specific exception?\n        print('!! Error with LEASTSQ fit, use L-BFGS-B instead')\n        p = minimize(pdf2use, prm0, args=(x, n), method='lbfgs')"
new_block_fit_2 = "    # use 'leastsq' or 'lbfgs' fit if error with min_method fit\n    try:\n        p = minimize(pdf2use, prm0, args=(x, n), method=min_method,\n            xtol=xtol, ftol=ftol)\n        if p.params['mu'] == 0:\n            raise ValueError(\"Mu parameter is zero, which is invalid.\")\n    except:\n        print(f\"'!! Error with {min_method} fit, use LEASTSQ instead'\")\n        try:\n            p = minimize(pdf2use, prm0, args=(x, n), method='leastsq',\n                xtol=xtol, ftol=ftol)\n        except ValueError:\n            raise\n        except:\n            # TODO: do we expect a specific exception?\n            print('!! Error with LEASTSQ fit, use L-BFGS-B instead')\n            p = minimize(pdf2use, prm0, args=(x, n), method='lbfgs')"


def get_package_file_path(package_name, module_name=None):
    """
    Returns the absolute path of the .py file of an installed package or module.
    - package_name : name of the package (e.g., 'rsr')
    - module_name : name of the module (e.g., 'sample'), or None for the __init__.py of the package
    """
    if module_name:
        full_name = f"{package_name}.{module_name}"
    else:
        full_name = package_name
    spec = importlib.util.find_spec(full_name)
    if spec is None or spec.origin is None:
        raise ImportError(f"Could not find {full_name}")
    return os.path.abspath(spec.origin)


def replace_block_in_file(filepath, old_block, new_block):
    """
    Replace in `filepath` the block of lines corresponding to `old_block`
    with `new_block`. If the block is not found exactly, raise an error.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    old_lines = old_block.strip('\n').splitlines()
    n_old = len(old_lines)
    found = False

    # Looking for the block
    for i in range(len(lines) - n_old + 1):
        # Compare each block of n_old lines
        if all(lines[i + j].rstrip('\n') == old_lines[j].rstrip('\n') for j in range(n_old)):
            found = True
            start_idx = i
            break

    if not found:
        raise ValueError("Correction of the rsr package impossible : maybe a update is needed")

    # Replacement
    new_lines = [l + '\n' for l in new_block.strip('\n').splitlines()]
    lines = lines[:start_idx] + new_lines + lines[start_idx + n_old:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    print(f"Block replaced in {filepath} (lines {start_idx+1} to {start_idx+n_old})")


if __name__ == "__main__":

    old_blocks = [old_block_fit_1, old_block_fit_2, 
                  old_block_run_1, old_block_run_2]
    new_blocks = [new_block_fit_1, new_block_fit_2, 
                  new_block_run_1, new_block_run_2]

    filepath_fit = get_package_file_path('rsr', 'fit')
    filepath_run = get_package_file_path('rsr', 'run')

    replace_block_in_file(filepath_fit, old_blocks[0], new_blocks[0])
    replace_block_in_file(filepath_fit, old_blocks[1], new_blocks[1])
    replace_block_in_file(filepath_run, old_blocks[2], new_blocks[2])
    replace_block_in_file(filepath_run, old_blocks[3], new_blocks[3])
    
    print("RSR package modification completed successfully.")
