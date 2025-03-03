import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta

def load_and_process_data(file_path):
    """
    Load CSV data and process columns:
      - Strip extra spaces in "Sewer Name"
      - Convert "Start Time" to datetime
      - Compute "End Time" using "Operation Time" (in minutes)
      - Sort operations by "Sewer Name" and then by "Start Time"
    """
    df = pd.read_csv(file_path)
    df["Sewer Name"] = df["Sewer Name"].str.strip()
    df["Start Time"] = pd.to_datetime(df["Start Time"], format='%Y-%m-%d %H:%M')
    df["End Time"] = df["Start Time"] + pd.to_timedelta(df["Operation Time"], unit="m")
    df = df.sort_values(["Sewer Name", "Start Time"])
    return df

def group_and_sort_sewers(df):
    """
    For each sewer, determine their dominant sew type based on total operation time in that type,
    then sort sewers within each group from the one that spends the most time in that sew type to the least.
    Returns the sorted list of sewers.
    """
    # Compute total operation time for each (Sewer, Sew Type)
    grouped = df.groupby(["Sewer Name", "Sew Type"])["Operation Time"].sum().reset_index()
    # For each sewer, pick the sew type with maximum operation time
    dominant = grouped.loc[grouped.groupby("Sewer Name")["Operation Time"].idxmax()]
    # Rename the dominant operation time column for clarity
    dominant = dominant.rename(columns={"Operation Time": "Dominant Time"})
    
    # Sort by Sew Type (alphabetically) and then by Dominant Time (descending)
    dominant_sorted = dominant.sort_values(by=["Sew Type", "Dominant Time"], ascending=[True, False])
    sorted_sewers = dominant_sorted["Sewer Name"].tolist()
    return sorted_sewers

def generate_gantt_chart(df, sorted_sewers):
    """
    Generate a horizontal Gantt chart with:
      - Operations as horizontal bars (start to end time)
      - Color coding based on "Sew Type"
      - x-axis formatted in hourly intervals
    """
    # Create a color mapping for each unique Sew Type using a colormap
    unique_sew_types = df["Sew Type"].unique()
    colors = plt.cm.tab20.colors  # A colormap with many distinct colors
    color_map = {stype: colors[i % len(colors)] for i, stype in enumerate(unique_sew_types)}
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create a mapping for y-axis positions based on sorted sewers
    y_positions = {sewer: i for i, sewer in enumerate(sorted_sewers)}
    
    # Plot each operation as a horizontal bar
    for _, row in df.iterrows():
        y = y_positions[row["Sewer Name"]]
        start = row["Start Time"]
        end = row["End Time"]
        # Compute duration in days (Matplotlib dates are in days)
        duration = (end - start).total_seconds() / (3600 * 24)
        ax.barh(y, duration, left=start, height=0.4, color=color_map[row["Sew Type"]], edgecolor='black')
    
    # Set y-axis labels
    ax.set_yticks(list(y_positions.values()))
    ax.set_yticklabels(sorted_sewers)
    
    # Format x-axis as dates with hourly ticks
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    
    # Set x-axis limits based on the earliest and latest times in the data
    min_start = df["Start Time"].min()
    max_end = df["End Time"].max()
    ax.set_xlim(min_start, max_end)
    
    ax.set_xlabel("Time")
    ax.set_title("Sewing Progressive Set Schedule")
    
    # Create a legend for Sew Types
    handles = [plt.Rectangle((0, 0), 1, 1, color=color_map[stype]) for stype in unique_sew_types]
    ax.legend(handles, unique_sew_types, title="Sew Type")
    
    plt.tight_layout()
    plt.show()

def select_file_and_visualize():
    """
    Opens a file dialog to select the CSV file, processes the data,
    and generates the Gantt chart. Errors are displayed in a popup.
    """
    file_path = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV files", "*.csv")])
    if file_path:
        try:
            df = load_and_process_data(file_path)
            sorted_sewers = group_and_sort_sewers(df)
            generate_gantt_chart(df, sorted_sewers)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

def main():
    # Create the main window
    root = tk.Tk()
    root.title("Sewing Production Schedule Gantt Chart")
    root.geometry("350x150")
    
    # Create and place the button to select a CSV file
    select_button = tk.Button(root, text="Select CSV File", command=select_file_and_visualize, width=25, height=2)
    select_button.pack(expand=True)
    
    root.mainloop()

if __name__ == "__main__":
    main()
