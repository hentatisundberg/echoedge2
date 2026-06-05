#Load libraries
from pathlib import Path
try:
    import moviepy.editor as mpy
except Exception:
    # Some moviepy installations expose functionality at package root (no editor submodule)
    import moviepy as mpy
import glob
import imagesize
import pandas as pd
import cv2
import datetime
import os
import sys
import yaml
from yaml.loader import SafeLoader



# Prepare output folders and clear old files
os.makedirs("dump", exist_ok=True)
os.makedirs("dump/added", exist_ok=True)
os.makedirs("dump/added_cropped", exist_ok=True)

# clear any files in the two output folders and any old gifs/mp4s in dump
for f in glob.glob("dump/added/*"):
    try:
        os.remove(f)
    except Exception:
        pass
for f in glob.glob("dump/added_cropped/*"):
    try:
        os.remove(f)
    except Exception:
        pass
for f in glob.glob("dump/*.gif") + glob.glob("dump/*.mp4"):
    try:
        os.remove(f)
    except Exception:
        pass



# Load all params from yaml-file
with open(sys.argv[1], 'r') as f:
    params = list(yaml.load_all(f, Loader=SafeLoader))



#Create a sorted list with all the png files in our directory
# HERE - add if there are special file endings that needs to be considered!
file_list = sorted(glob.glob(params[0]['img_path'])) 


#name of the animation
gif_name = params[0]['output_name']

# Image height 
image_height = params[0]['img_height']
# Target width to produce before cropping (keep images consistent)
target_width = params[0]['target_width']


# Check image size of all images 
ws = []
hs = []
for file in file_list: 
    width, height = imagesize.get(file)
    ws.append(width)
    hs.append(height) 

# Subset file list based on image size
include = []
final_list = []
filelength = []
for i in range(0, len(ws)): 
    if (ws[i] > 10 and hs[i] == image_height):
        include.append(1)
        final_list.append(file_list[i])
        filelength.append(ws[i])
    else:
        include.append(0) 

# Date for each file 
date = []

for file in final_list:
    t = Path(file)
    date.append(t.name.split("-")[2][1:]) 
    
dates = []
for x in date:
    if x not in dates:
        dates.append(x)


# Stack images  
# horizontally concatenates images 
# of same height  




tempfiles = []
counter = 0
imcounter = 0 
length = 0
# Keep track of concatenated filenames we produce so later steps use the same list
concat_files = []


for i in range(0, len(final_list)):
    w = filelength[i]
    
    # Check if adding this image would exceed target_width
    if length + w > target_width and len(tempfiles) > 0:
        # Flush current batch first
        images = [cv2.imread(f) for f in tempfiles]
        # Filter out any None values from corrupted/unreadable images
        images = [img for img in images if img is not None]
        if len(images) == 0:
            print(f"Warning: All images in batch failed to load, skipping batch")
            tempfiles = []
            counter = 0
            length = 0
            continue
        im_h = cv2.hconcat(images)
        d1, t1 = Path(tempfiles[0]).name.split("-")[2:4]
        dx1 = datetime.datetime.strptime(d1+t1, "D%Y%m%dT%H%M%S") 
        str1 = dx1.strftime("%d %B, %H:%M")
        d2, t2 = Path(tempfiles[-1]).name.split("-")[2:4]
        dx2 = datetime.datetime.strptime(d2+t2, "D%Y%m%dT%H%M%S") 
        str2 = dx2.strftime(" - %H:%M")
        str3 = str1+str2
        text = str3
        font = cv2.FONT_HERSHEY_SIMPLEX
        # place text near the bottom-right but keep it inside image bounds
        org_x = max(10, min(1900, im_h.shape[1] - 200))
        org_y = max(10, min(im_h.shape[0] - 50, 1450))
        org = (org_x, org_y)
        fontScale = 2
        color = (0, 0, 255)
        thickness = 2
        im_h = cv2.putText(im_h, text, org, font, fontScale, 
                        color, thickness, cv2.LINE_AA, False)
        imcounter_fill = str(imcounter).zfill(4)
        # build filename prefixed with output_name and including the batch start timestamp
        start_ts = dx1.strftime('%Y%m%dT%H%M%S')
        concat_name = f"dump/added/{gif_name}_{start_ts}_{imcounter_fill}.png"
        cv2.imwrite(concat_name, im_h)
        concat_files.append(concat_name)
        # Reset for new batch
        tempfiles = []
        counter = 0
        imcounter += 1
        length = 0
    
    # Add current file to the batch
    tempfiles.append(final_list[i])
    counter += 1
    length += w

# After loop, flush any remaining images ONLY if they form a reasonably sized batch
# (We skip the last partial batch to avoid making all images too small)
if len(tempfiles) > 0:
    # Calculate what the final batch width would be
    final_batch_width = sum([filelength[final_list.index(f)] for f in tempfiles])
    # Only include this batch if it's at least 50% of target_width
    # Otherwise skip it to maintain better quality for all other images
    if final_batch_width >= target_width * 0.5:
        images = [cv2.imread(f) for f in tempfiles]
        # Filter out any None values from corrupted/unreadable images
        images = [img for img in images if img is not None]
        if len(images) == 0:
            print(f"Warning: All images in final batch failed to load, skipping batch")
        else:
            im_h = cv2.hconcat(images)
            d1, t1 = Path(tempfiles[0]).name.split("-")[2:4]
            dx1 = datetime.datetime.strptime(d1+t1, "D%Y%m%dT%H%M%S") 
            str1 = dx1.strftime("%d %B, %H:%M")
            d2, t2 = Path(tempfiles[-1]).name.split("-")[2:4]
            dx2 = datetime.datetime.strptime(d2+t2, "D%Y%m%dT%H%M%S") 
            str2 = dx2.strftime(" - %H:%M")
            str3 = str1+str2
            text = str3
            font = cv2.FONT_HERSHEY_SIMPLEX
            org_x = max(10, min(1900, im_h.shape[1] - 200))
            org_y = max(10, min(im_h.shape[0] - 50, 1450))
            org = (org_x, org_y)
            fontScale = 2
            color = (0, 0, 255)
            thickness = 2
            im_h = cv2.putText(im_h, text, org, font, fontScale, 
                            color, thickness, cv2.LINE_AA, False)
            imcounter_fill = str(imcounter).zfill(4)
            start_ts = dx1.strftime('%Y%m%dT%H%M%S')
            concat_name = f"dump/added/{gif_name}_{start_ts}_{imcounter_fill}.png"
            cv2.imwrite(concat_name, im_h)
            concat_files.append(concat_name)
            print(f"Included final batch with width {final_batch_width} -> {concat_name}")
    else:
        print(f"Skipped final batch with width {final_batch_width} (less than 50% of target {target_width})")



# Check resulting size of images and cut horizontally to get equal size
# We use the list of concatenated files we created above (concat_files)
file_list = sorted(concat_files)

# Check image size of all combined images 
ws = []
hs = []
for file in file_list: 
    width, height = imagesize.get(file)
    ws.append(width)
    hs.append(height) 

# Use the minimum width to ensure all cropped images have same size
crop_width = min(ws) if ws else target_width
print(f"Cropping all images to width: {crop_width}")

# Cut to match minimum width
counter = 0
for file in file_list: 
    im = cv2.imread(file)
    im_crop = im[:, 0:crop_width]
    filenum = str(counter).zfill(4)
    cv2.imwrite(f'dump/added_cropped/{filenum}.png', im_crop)
    counter += 1



# Just take 20 images at the time... 
combined = sorted(glob.glob("dump/added_cropped/*"))

for file in combined: 
    width, height = imagesize.get(file)
    print(file, width, height)


#frames per second
fps = params[0]['fps']

#Create a clip instance using ImageSequenceClip included in moviepy
clip = mpy.ImageSequenceClip(combined, fps=fps)

#No we can write the animation as a a gif
clip.write_gif("dump/"+gif_name+'.gif')

#No we can write the animation as a a mp4
clip.write_videofile("dump/"+gif_name+'.mp4')


# Run example
# python3 postprocessing/animation/animating_echogram2.py  postprocessing/animation/params_animation_baltic25.yaml