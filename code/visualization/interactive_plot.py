


import echopype as ep
import matplotlib.pyplot as plt
import xarray as xr
import hvplot.xarray  # for interactive plots


# Set params
waveform = "BB"
encode = "complex"

# Open existing zarr
#zarr_path = "Hake-D20230811-T165727.zarr"
#ed = ep.open_converted(zarr_path, chunks={})

# Open new raw file
raw_path = "F:/DATA_HUDSON/RAW_FILES/MissionPlanHudsonBay2024V1-Phase0-D20240707-T190111-0.raw"

env_params = {
  "temperature": 2,
  "salinity": 9,
  "pressure": 10.1325
}
 

cal_params ={
  "gain_correction": 28.49,
  "equialent_beam_angle": -21
}

ed = ep.open_raw(raw_path, sonar_model="EK80")
    
ds_Sv_raw = ep.calibrate.compute_Sv(
        ed,
        env_params = env_params,
        cal_params = cal_params,
        waveform_mode=waveform,
        encode_mode="complex",
)

ds_MVBS = ep.commongrid.compute_MVBS(
        ds_Sv_raw, # calibrated Sv dataset
        range_meter_bin=0.1, # bin size to average along range in meters
        ping_time_bin='3s' # bin size to average along ping_time in seconds
)



ds_MVBS = ds_MVBS.swap_dims({"channel": "frequency_nominal"})

plot = ds_MVBS["Sv"].hvplot.quadmesh(
    x="ping_time", clim=(-95, -40), figsize=(12, 12), cmap="RdYlBu_r", rasterize=True,
    groupby="frequency_nominal"
).opts(invert_yaxis=True, height=400)
hvplot.show(plot)

