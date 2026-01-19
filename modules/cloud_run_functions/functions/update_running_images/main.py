import os
import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import functions_framework
from google.cloud import storage

@functions_framework.http
def update_running_images(request):
    """
    An HTTP-triggered function that reads a CSV from GCS, generates a plot,
    and saves it to another GCS bucket.
    Args:
        request (flask.Request): The request object. Not used in this function.
    Returns:
        A string with the public URL of the generated chart.
    """
    # --- Configuration ---
    data = request.get_json()
    data_bucket_name = data["SOURCE_BUCKET"]
    chart_bucket_name = data["DESTINATION_BUCKET"]
    csv_file_name = "garmin_activities.csv"
    output_chart_name = "running__base_runs_weekly_avg_pace.png"

    if not data_bucket_name or not chart_bucket_name:
        return "Error: DATA_BUCKET and CHART_BUCKET environment variables must be set.", 500

    # --- 1. Load Data from GCS ---
    try:
        gcs_path = f"gs://{data_bucket_name}/{csv_file_name}"
        df = pd.read_csv(gcs_path)
        # Filter for "Base" runs
        df = df[(df['sport'] == 'running') & (df['name'].str.contains('Base|Long Run', na=False))]
    except Exception as e:
        return f"Error reading from GCS: {e}", 500

    # --- 2. Corrected Data Preparation (using moving_time) ---

    # Use the 'start_time' column for the date and convert it
    df['Date'] = pd.to_datetime(df['start_time'])

    # Convert 'distance' from meters to kilometers
    df['Distance'] = pd.to_numeric(df['distance'], errors='coerce') 

    # Use 'avg_hr' for the heart rate
    df['Avg HR'] = pd.to_numeric(df['avg_hr'], errors='coerce')

    # Rename 'name' and 'sport' for consistency
    df.rename(columns={'name': 'Name', 'sport': 'Sport'}, inplace=True)

    # 'errors=coerce' will turn any bad time formats into NaT (Not a Time)
    df['Total Time'] = pd.to_timedelta(df['moving_time'], errors='coerce').dt.total_seconds() / 60
    # ===================================================================

    # Drop any rows where the time conversion failed, or other essential data is missing
    df.dropna(subset=['Date', 'Distance', 'Avg HR', 'Total Time'], inplace=True)

    # Calculate 'Avg Pace' in min/km now that 'Total Time' is reliable
    # Replace infinite values (from distance=0) with NaN so they can be dropped
    df['Avg Pace Numeric'] = (df['Total Time'] / df['Distance']).replace([np.inf, -np.inf], np.nan)
    df.dropna(subset=['Avg Pace Numeric'], inplace=True)

    # Calculate a "time-weighted" HR value for accurate weekly averaging
    df['Time x Avg HR'] = df['Total Time'] * df['Avg HR']

    # Set the 'Date' column as the index for time-series analysis
    df.set_index('Date', inplace=True)

    # --- 3. Aggregate Data by Week ---
    weekly_sums = df[['Distance', 'Total Time', 'Time x Avg HR']].resample('W-MON', label='left', closed='left').sum()
    weekly_sums['Weighted Avg Pace'] = weekly_sums['Total Time'] / weekly_sums['Distance']
    weekly_sums['Weighted Avg HR'] = weekly_sums['Time x Avg HR'] / weekly_sums['Total Time']
    weekly_data = weekly_sums[['Weighted Avg Pace', 'Weighted Avg HR']].dropna()

    # --- 4 & 5. Create the Plot & Customize (No changes needed) ---
    # The rest of your plotting code is correct and does not need to be changed.

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax1 = plt.subplots(figsize=(15, 8))

    # Plot 1: Weekly Average Pace
    color1 = 'tab:blue'
    ax1.set_ylabel('Average Pace (min/km)', color=color1, fontsize=12, weight='bold')
    ax1.plot(weekly_data.index, weekly_data['Weighted Avg Pace'], color=color1, marker='o', linestyle='-', label='Avg Pace')
    ax1.tick_params(axis='y', labelcolor=color1)

    def format_pace(decimal_minutes, pos):
        if pd.isna(decimal_minutes) or decimal_minutes <= 0: return ""
        minutes = int(decimal_minutes)
        seconds = int((decimal_minutes * 60) % 60)
        return f'{minutes:02d}:{seconds:02d}'
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(format_pace))

    # Plot 2: Weekly Average HR
    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Average Heart Rate (bpm)', color=color2, fontsize=12, weight='bold')
    ax2.plot(weekly_data.index, weekly_data['Weighted Avg HR'], color=color2, marker='s', linestyle='--', label='Avg HR')
    ax2.tick_params(axis='y', labelcolor=color2)

    ax1.axhline(y=6.5, color='cyan', linestyle='--', label='Pace Goal (6:30)')
    ax2.axhline(y=150, color='orange', linestyle='--', label='HR Goal (150)')

    for week, data_point in weekly_data.iterrows():
        pace_value = data_point['Weighted Avg Pace']
        total_distance = weekly_sums.loc[week, 'Distance']
        ax1.annotate(f'{total_distance:.0f}',
                    xy=(week, pace_value),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=9,
                    color='navy')

    ax1.set_title('Weekly Average Pace and Heart Rate vs. Targets', fontsize=16, weight='bold')
    ax1.set_xlabel('Week', fontsize=12)

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='upper right')

    fig.tight_layout()

    # --- 5. Save Plot to GCS Bucket ---
    storage_client = storage.Client()
    bucket = storage_client.bucket(chart_bucket_name)
    blob = bucket.blob(output_chart_name)
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150)
    img_buffer.seek(0)
    blob.upload_from_file(img_buffer, content_type='image/png')
    plt.close(fig)

    return f"Chart successfully generated and saved to: {blob.public_url}", 200