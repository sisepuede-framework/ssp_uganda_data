1. Go to postprocessing_process_250820.r and make sure the paths are correct. Then change the year_ref to 2020 or 2022.
2. When you have 2020 and 2022 emissions data go to combine_tableau_output_files.ipynb to combine dataframes.
3. Once you get the combined csv you need to process it twice using overwrite_sectors notebook with both years.
4. You should get two overwritten files than now need to be combined in combine_tableau_overwritten_files.ipynb.