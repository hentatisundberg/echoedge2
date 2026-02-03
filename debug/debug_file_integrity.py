import numpy as np
import warnings
import sys
import yaml
import os
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), '../../lib'))

from yaml.loader import SafeLoader
from find_bottom import find_bottom
from export_data import save_data
from find_fish import find_fish_median, medianfun
from visualization import data_to_images
from processing import process_data, clean_times, remove_vertical_lines
from find_waves import find_waves, find_layer

# Load all params from yaml-file
with open(sys.argv[1], 'r') as f:
    params = list(yaml.load_all(f, Loader=SafeLoader))


path = sys.argv[2]

echodata, ping_times = process_data(path, params[0]['env_params'], params[0]['cal_params'], params[0]['bin_size'], 'BB')

print(echodata)

#run example
"""

# Not working 
python3 debug/debug_file_integrity.py edge/sailor/paramsBaltic2025.yaml ../../../../../../mnt/BSP_NAS2/Acoustics/Sailor_other/2025/Finngrundet/Raw_files/SLUAquaSailor2020V2-Phase0-D20251023-T000142-0.raw

# Not working 
python3 debug/debug_file_integrity.py edge/sailor/paramsBaltic2025.yaml ../../../../../../mnt/BSP_NAS2/Acoustics/Sailor_other/2025/Finngrundet/Raw_files/SLUAquaSailor2020V2-Phase0-D20251017-T174115-0.raw

# Working 
python3 debug/debug_file_integrity.py edge/sailor/paramsBaltic2025.yaml ../../../../../../mnt/BSP_NAS2/Acoustics/Sailor_other/2025/Finngrundet/Raw_files/SLUAquaSailor2020V2-Phase0-D20251111-T100111-0.raw


"""