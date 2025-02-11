import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt
from skimage.morphology import binary_dilation,rectangle 
import numpy.ma as ma
import skimage
import sys
import cv2
from tqdm import tqdm
import os
import pickle

from Double_thresh_function import npy_correction_v3,parameters_correction



# PATH #################################################################################
path_npy = "F:/DATA_HUDSON/PROCESS/Resize"# Resize image
dest_path_png = "F:/DATA_HUDSON/PROCESS/Mask" # Where the masked image will be saved
csv_path = 'F:/DATA_HUDSON/PROCESS/csv' #Csv file from the first output
######################################################################################

if not os.path.exists(dest_path_png):
    # Create the directory if it doesn't exist
    os.makedirs(dest_path_png)

files = os.listdir(path_npy)
files_npy = [file for file in files if file.endswith('.npy')]
for file in tqdm(files_npy):
    file_path = os.path.join(path_npy,file)
    img = np.load(file_path)
    min_pixel_intensity = np.min(img)
    if min_pixel_intensity > -150:                               
        csv_name = file.replace('_new.npy','.csv')
        csv_table = pd.read_csv(os.path.join(csv_path,csv_name))
        median_sea_depth = np.median(csv_table['depth'])

        shape_top,shape_bottom,total_rows,shape_top_desc,shape_bottom_desc = parameters_correction(img,median_sea_depth,threshold = -30)    
        # Step 1 : mask the image 
        im = npy_correction_v3(img,total_rows,shape_top,shape_bottom)         # 1 change
        plt.imsave(f'{dest_path_png}/{file[:-4]}.png',im)