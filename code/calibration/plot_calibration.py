#!/usr/bin/env python3
"""
plot_calibration.py

Usage:
    python plot_calibration.py cal_file1.csv cal_file2.csv ...

This script reads calibration CSV files and creates an interactive plot
showing Gain vs Frequency for each calibration event (file).
"""

import sys
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

def extract_date_from_filename(filepath):
    """
    Extract a readable label from the filename.
    Tries to identify date patterns or uses the filename.
    """
    filename = Path(filepath).stem
    # You can customize this to better extract dates from your filenames
    # For now, just use the filename
    return filename

def plot_calibration_data(csv_files):
    """
    Read multiple CSV files and plot Gain vs Frequency for each.
    If a file has a 'Date' column, create separate series for each date.
    """
    if not csv_files:
        print("Error: No CSV files provided")
        sys.exit(1)
    
    fig = go.Figure()
    
    for csv_file in csv_files:
        try:
            # Read the CSV file (handle both comma and semicolon separators)
            # Use decimal=',' to handle European decimal format
            # Use encoding='utf-8-sig' to handle BOM
            df = pd.read_csv(csv_file, sep=None, engine='python', decimal=',', encoding='utf-8-sig')
            
            # Check if required columns exist
            if 'Frequency' not in df.columns or 'Gain' not in df.columns:
                print(f"Warning: {csv_file} missing 'Frequency' or 'Gain' columns, skipping...")
                continue
            
            # Convert to numeric, coerce errors to NaN
            df['Frequency'] = pd.to_numeric(df['Frequency'], errors='coerce')
            df['Gain'] = pd.to_numeric(df['Gain'], errors='coerce')
            
            # Check if there's a Date column for grouping
            if 'Date' in df.columns:
                # Group by Date and create a separate series for each
                for date, group in df.groupby('Date'):
                    # Remove rows with NaN values
                    group_clean = group[['Frequency', 'Gain']].dropna()
                    
                    if group_clean.empty:
                        continue
                    
                    # Sort by frequency for better line plots
                    group_clean = group_clean.sort_values('Frequency')
                    
                    # Build label with date, platform, and location
                    label = str(date)
                    if 'Platform' in df.columns and 'Location' in df.columns:
                        platform = group['Platform'].iloc[0] if not group['Platform'].empty else ''
                        location = group['Location'].iloc[0] if not group['Location'].empty else ''
                        if platform or location:
                            label = f"{date} - {platform} - {location}"
                    
                    # Add trace to the plot
                    fig.add_trace(go.Scatter(
                        x=group_clean['Frequency'],
                        y=group_clean['Gain'],
                        mode='lines+markers',
                        name=label,
                        hovertemplate=(
                            '<b>%{fullData.name}</b><br>' +
                            'Frequency: %{x:.1f} Hz<br>' +
                            'Gain: %{y:.4f} dB<br>' +
                            '<extra></extra>'
                        )
                    ))
                    
                    print(f"Added {len(group_clean)} points for date {date} from {csv_file}")
            else:
                # No Date column, treat entire file as one series
                # Remove rows with NaN values
                df_clean = df[['Frequency', 'Gain']].dropna()
                
                if df_clean.empty:
                    print(f"Warning: {csv_file} has no valid data, skipping...")
                    continue
                
                # Sort by frequency for better line plots
                df_clean = df_clean.sort_values('Frequency')
                
                # Extract label from filename
                label = extract_date_from_filename(csv_file)
                
                # Add trace to the plot
                fig.add_trace(go.Scatter(
                    x=df_clean['Frequency'],
                    y=df_clean['Gain'],
                    mode='lines+markers',
                    name=label,
                    hovertemplate=(
                        '<b>%{fullData.name}</b><br>' +
                        'Frequency: %{x:.1f} Hz<br>' +
                        'Gain: %{y:.4f} dB<br>' +
                        '<extra></extra>'
                    )
                ))
                
                print(f"Added {len(df_clean)} points from {csv_file}")
            
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")
            continue
    
    if not fig.data:
        print("Error: No valid data to plot")
        sys.exit(1)
    
    # Update layout
    fig.update_layout(
        title='Calibration Data: Gain vs Frequency',
        xaxis_title='Frequency (Hz)',
        yaxis_title='Gain (dB)',
        hovermode='closest',
        template='plotly_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        width=1200,
        height=700
    )
    
    # Show the plot in browser
    fig.show()
    
    # Optionally save to HTML
    output_file = 'calibration_plot.html'
    fig.write_html(output_file)
    print(f"\nPlot saved to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plot_calibration.py cal_file1.csv cal_file2.csv ...")
        print("\nExample:")
        print("python3 code/calibration/plot_calibration.py temp/cal_hudson2025.csv temp/cal_karlso2025.csv")
        sys.exit(1)
    
    csv_files = sys.argv[1:]
    plot_calibration_data(csv_files)

# Run example:
# python3 code/calibration/plot_calibration.py temp/cal_hudson2025.csv temp/cal_karlso2025.csv
