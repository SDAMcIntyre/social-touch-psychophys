import os
# os.environ["MPLBACKEND"] = "Agg"  # Use a non-interactive backend

import matplotlib
matplotlib.use('TkAgg')  # or 'Qt5Agg'

import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import re
from scipy.signal import correlate2d
import shutil
import sys
import warnings

# homemade libraries
# current_dir = Path(__file__).resolve()
sys.path.append(str(Path(__file__).resolve().parent.parent))
import libraries.misc.path_tools as path_tools  # noqa: E402
import numpy as np



def plot_with_synced_zoom(df1, df2, df3, colnames=None, labels = None, title_str = ""):
    if colnames is None:
        colnames = df1.columns
    if labels is None:
        labels = ["df1", "df2", "df3"]

    # Create subplots
    fig, axes = plt.subplots(nrows=len(colnames), ncols=1, figsize=(8, len(colnames) * 4))
    
    # Plot each column
    for i, column in enumerate(colnames):
        if df1 is not None:
            axes[i].plot(df1[column], label=labels[0])#, marker='x', linestyle='None')
        if df2 is not None:
            axes[i].plot(df2[column], label=labels[1])
        if df3 is not None:
            axes[i].plot(df3[column], label=labels[2], linestyle=(0, (5, 10)), color='black')
        
        axes[i].set_title(f'{column}')
        axes[i].legend()
    
    plt.suptitle(title_str)
    plt.show(block=True)



def find_best_offset(matrix1, matrix2, offset_bounds=(-120, 120), num_offsets=None, verbose=False):
    # Replace NaN values with 0
    matrix1 = np.nan_to_num(matrix1, nan=0.0)
    matrix2 = np.nan_to_num(matrix2, nan=0.0)

    # Adjust the bounds to be within the valid range
    min_offset = int(max(offset_bounds[0], -matrix1.shape[0] + 1))
    max_offset = int(min(offset_bounds[1], matrix1.shape[0] - 1))
    
    if verbose:
        print(f"Offset bounds adjusted to: ({min_offset}, {max_offset})")
    
    # Determine the step size for offsets
    if num_offsets is not None:
        step_size = int(max(1, (max_offset - min_offset) // num_offsets))
    else:
        step_size = 1
    
    if verbose:
        print(f"Step size for offsets: {step_size}")
    
    # Find the index of the maximum correlation within the specified offset range
    max_correlation = -np.inf
    best_offset = 0
    
    total_steps = (max_offset - min_offset) // step_size + 1
    current_step = 0
    last_printed_progress = -1
    
    for offset in range(min_offset, max_offset + 1, step_size):
        current_step += 1
        progress = (current_step / total_steps) * 100
        progress_int = int(progress)
        
        if verbose and progress_int != last_printed_progress:
            print(f"Progress: {progress_int}%")
            last_printed_progress = progress_int
        
        # Create a zero-padded version of matrix2 based on the offset
        if offset > 0:
            matrix2_offset = np.pad(matrix2, ((offset, 0), (0, 0)), mode='constant', constant_values=0)[:-offset, :]
        elif offset < 0:
            matrix2_offset = np.pad(matrix2, ((0, -offset), (0, 0)), mode='constant', constant_values=0)[-offset:, :]
        else:
            matrix2_offset = matrix2
        
        # Flatten the matrices to 1D arrays
        flat_matrix1 = np.array(matrix1).flatten()
        flat_matrix2 = np.array(matrix2_offset).flatten()
        
        # Calculate the correlation coefficient
        correlation_value = np.corrcoef(flat_matrix1, flat_matrix2)[0, 1]

        if correlation_value > max_correlation:
            max_correlation = correlation_value
            best_offset = offset
    
    return best_offset, max_correlation



if __name__ == "__main__":
    # parameters
    verbose = True
    show = True  # If user wants to monitor what's happening
    show_steps = False

    force_processing = False  # If user wants to force data processing even if results already exist
    save_results = True

    print("Step 0: Extract the data embedded in the selected sessions.")
    # get database directory and input base directory
    db_path_target_contact = os.path.join(path_tools.get_database_path(), "semi-controlled", "3_merged", "archive", "contact_and_neural")
    db_path_target_contact_input = os.path.join(db_path_target_contact, "new_axes_3Dposition")  # manual_axes, manual_axes_3Dposition_RF, new_axes, new_axes_3Dposition

    db_path = os.path.join(path_tools.get_database_path(), "semi-controlled", "3_merged", "1_kinect_and_nerve_shandata")
    db_path_input = os.path.join(db_path, "0_0_by-units")

    # get output base directory
    db_path_output = os.path.join(db_path, "0_1_by-units_correct-contact")
    if save_results and not os.path.exists(db_path_output):
        os.makedirs(db_path_output)
        print(f"Directory '{db_path_output}' created.")

    # Session names
    sessions_ST13 = ['2022-06-14_ST13-01',
                     '2022-06-14_ST13-02',
                     '2022-06-14_ST13-03']

    sessions_ST14 = ['2022-06-15_ST14-01',
                     '2022-06-15_ST14-02',
                     '2022-06-15_ST14-03',
                     '2022-06-15_ST14-04']

    sessions_ST15 = ['2022-06-16_ST15-01',
                     '2022-06-16_ST15-02']

    sessions_ST16 = ['2022-06-17_ST16-02',
                     '2022-06-17_ST16-03',
                     '2022-06-17_ST16-04',
                     '2022-06-17_ST16-05']

    sessions_ST18 = ['2022-06-22_ST18-01',
                     '2022-06-22_ST18-02',
                     '2022-06-22_ST18-04']
    sessions = []
    sessions = sessions + sessions_ST13
    sessions = sessions + sessions_ST14
    sessions = sessions + sessions_ST15
    sessions = sessions + sessions_ST16
    sessions = sessions + sessions_ST18
    
    # column names for raw contact characteristics
    colnames_contact = ["areaRaw", "depthRaw", "velAbsRaw", "velLatRaw", "velLongRaw", "velVertRaw"]
    colnames_contact_xcorr = ["velAbsRaw", "areaRaw", "depthRaw"]
    colnames_contact_processed = ["area", "areaSmooth", "area1D", "area2D",
                                  "depth", "depthSmooth", "depth1D", "depth2D", 
                                  "velAbs", "velAbsSmooth", "velAbs1D", "velAbs2D",
                                  "velLat", "velLatSmooth", "velLat1D", "velLat2D",
                                  "velLong", "velLongSmooth", "velLong1D", "velLong2D",
                                  "velVert", "velVertSmooth", "velVert1D", "velVert2D"]

    for session in sessions:
        session_shan = re.sub(r'_(ST\d+)-0*(\d+)', r'-\1-unit\2', session)
        file = [f.name for f in Path(db_path_input).iterdir() if session_shan in f.name]
        if len(file) != 1:
            warnings.warn(f"Issue detected: not exactly 1 csv file found for {session}.")
            continue
        file = file[0]
        file_abs = os.path.join(db_path_input, file)
        file_contact_abs = os.path.join(db_path_target_contact_input, file)
        
        output_filename = f"{session}_semicontrolled.csv"
        output_filename_abs = os.path.join(db_path_output, output_filename)
        if not force_processing and os.path.exists(output_filename_abs):
            continue
    
        # load current data
        data_sept = pd.read_csv(file_abs)
        data_jan = pd.read_csv(file_contact_abs)
        print(f'{session}: data has {len(data_sept)} samples. data_contact has {len(data_jan)}')
        
        # remove the processed contact characteristics columns
        data_sept = data_sept.drop(columns=colnames_contact_processed)
        data_jan = data_jan.drop(columns=colnames_contact_processed)

        # Cut the dataframes into chunks for each block_id value
        unique_block_ids_sept = data_sept['block_id'].unique()
        unique_block_ids_jan = data_jan['block_id'].unique()
            
        # Check if they are similar
        if not set(unique_block_ids_sept) == set(unique_block_ids_jan):
            warnings.warn("The unique block IDs in September and January datasets are not similar!")

        # Initialize data_result with the same columns as data_sept but no content
        data_result = pd.DataFrame(columns=data_sept.columns)

        for block_id in unique_block_ids_sept:
            chunk_sept = data_sept[data_sept['block_id'] == block_id]
            chunk_jan = data_jan[data_jan['block_id'] == block_id]
            
            if chunk_sept.empty or chunk_jan.empty:
                continue

            # Calculate the range offset of the signals correlation
            index_sept = chunk_sept.index[-1]
            index_jan = chunk_jan.index[-1]
            offset_block = np.abs(index_sept - index_jan)
            offset_bounds = [-offset_block, offset_block]
            num_offsets = np.floor(1.00 * (offset_bounds[1] - offset_bounds[0]))

            # Generate equal matrices
            contact_data_sept = chunk_sept[colnames_contact]
            contact_data_jan = chunk_jan[colnames_contact]
            rows_jan = contact_data_jan.shape[0]
            rows_sept = contact_data_sept.shape[0]

            if rows_jan < rows_sept:
                rows_to_add = rows_sept - rows_jan
                empty_rows = pd.DataFrame(index=range(rows_to_add), columns=contact_data_jan.columns)
                contact_data_jan = pd.concat([contact_data_jan, empty_rows], ignore_index=True)
            elif rows_sept < rows_jan:
                rows_to_add = rows_jan - rows_sept
                empty_rows = pd.DataFrame(index=range(rows_to_add), columns=contact_data_sept.columns)
                contact_data_sept = pd.concat([contact_data_sept, empty_rows], ignore_index=True)

            contact_data_sept = contact_data_sept.reset_index(drop=True)
            contact_data_jan = contact_data_jan.reset_index(drop=True)

            # Compare the same column name of each dataset and correlate them to get the delay
            best_offset, max_correlation = find_best_offset(contact_data_sept[colnames_contact_xcorr], 
                                                            contact_data_jan[colnames_contact_xcorr], 
                                                            offset_bounds=offset_bounds, 
                                                            num_offsets=num_offsets,
                                                            verbose=verbose)
            print(f"Block ID {block_id}: The best offset is {best_offset} with a correlation of {max_correlation}.")

            corrected_contact_data_jan = contact_data_jan.shift(periods=best_offset)

            if show_steps:
                title_str = f'{session} - Block ID {block_id}: offset = {best_offset} samples'
                plot_with_synced_zoom(df1=contact_data_sept, df2=contact_data_jan, df3=corrected_contact_data_jan, 
                    labels = ["contact_data_sept", "contact_data_jan", "corrected_contact_data_jan"],
                    colnames=colnames_contact, 
                    title_str=title_str)

            chunk_sept = chunk_sept.reset_index(drop=True)
            # replace the september contact carac by the shifted january contact carac
            chunk_sept[colnames_contact] = corrected_contact_data_jan[colnames_contact]
            
            if data_result.empty:
                data_result = chunk_sept
            else:
                data_result = pd.concat([data_result, chunk_sept], ignore_index=True)

        if show:
            plt.plot(data_sept["spike"] - data_result["spike"])#, marker='x', linestyle='None')
            plt.suptitle("spikes difference between raw september and result (should be 0 everywhere)")
#            plt.show(block=True)

            plot_with_synced_zoom(df1=data_sept, df2=None, df3=data_result,
                labels = ["data_sept no correction", "", "data result, corrected"],
                colnames=["velAbsRaw", "spike"], 
                title_str="comparison before and after imported contact data")

        # save data on the hard drive ?
        if save_results:

            # Check if the folder exists
            if not os.path.exists(db_path_output):
                # Create the folder if it does not exist
                os.makedirs(db_path_output)
                
            # Excel indicates that the total path length,
            # including the filename and its directory structure,
            # exceeds the Windows maximum limit of 260 characters.
            data_result.to_csv(output_filename_abs, index=False)

        print("done.")

























