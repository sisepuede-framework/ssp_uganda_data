# Metamodel Workflow Guide

This document explains how to run the surrogate metamodel workflow in this repository. It is intended for new users who need to prepare training data and train the surrogate model from a SISEPUEDE run.

This guide covers:

- [`data_prep.ipynb`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/data_prep.ipynb)
- [`model_training.ipynb`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/model_training.ipynb)

Optimization is intentionally out of scope here.

## Workflow Summary

The metamodel workflow has two stages:

1. `data_prep.ipynb`
   Downloads a single SISEPUEDE run from S3, builds predictor features from Latin Hypercube Sample inputs, builds target variables from model outputs and cost-benefit outputs, and writes training datasets to local parquet files.
2. `model_training.ipynb`
   Loads the prepared parquet dataset, performs basic cleaning and exploratory checks, trains a multi-output XGBoost surrogate model, evaluates it, and saves the fitted model to disk.

At a high level, the flow is:

`AWS S3 run output -> local raw run files -> engineered training parquet -> trained XGBoost pipeline`

## Directory Layout

The workflow assumes the following structure under [`metamodel`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel):

- [`surrogate_model`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model): notebooks, configs, utilities, and trained model outputs
- [`data/ssp`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/data/ssp): downloaded raw SISEPUEDE run files
- [`data/training`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/data/training): engineered training datasets written by `data_prep.ipynb`

Important: both notebooks use `os.getcwd()` to define paths. Run them with the working directory set to [`metamodel/surrogate_model`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model), otherwise relative paths will break.

## Environment Setup

The repository includes [`environment.yml`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/environment.yml), which provides the main notebook environment.

Create and activate it with conda:

```bash
conda env create -f environment.yml
conda activate ssp_uganda_env
```

The metamodel notebooks also import packages that are not explicitly listed in `environment.yml`, including:

- `boto3`
- `xgboost`
- parquet support such as `pyarrow`
- `joblib`
- `PyYAML`

If any of those are missing in your environment, install them before running the notebooks.

To run the notebooks, register the environment as a Jupyter kernel if needed:

```bash
python -m ipykernel install --user --name ssp_uganda_env --display-name "Python (ssp_uganda_env)"
```

## AWS SSO Setup

The data preparation notebook pulls simulation outputs from S3 using a named AWS CLI profile. The profile name is read from [`ml_training_workflow_config.yaml`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/config/ml_training_workflow_config.yaml), and the notebook creates a boto3 session with that profile.

Use these AWS resources:

- AWS CLI SSO setup docs: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html#sso-configure-profile-token-auto-sso
- IAM Identity Center start page: https://d-9267a09e04.awsapps.com/start/#/?tab=accounts

### 1. Configure AWS CLI with SSO

Run:

```bash
aws configure sso
```

You will be prompted for:

- SSO start URL
- SSO region
- AWS account ID
- Role name
- CLI profile name

Use a profile name you will also place in the metamodel config, for example `tony-dev`.

### 2. Log in

Authenticate the profile before running the data preparation notebook:

```bash
aws sso login --profile tony-dev
```

When you are done working:

```bash
aws sso logout
```

### 3. Check S3 Access

Before opening the notebook, confirm the profile can see the target bucket:

```bash
aws s3 ls s3://sisepuede-data/ --profile tony-dev
```

If you need to manually inspect or sync files during debugging, these commands are useful:

```bash
aws s3 cp /path/to/local/folder s3://your-bucket-name/my_folder/ --recursive --profile tony-dev
aws s3 sync /path/to/local/folder s3://your-bucket-name/my_folder/ --profile tony-dev
```

## Configuration

The workflow is driven by [`ml_training_workflow_config.yaml`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/config/ml_training_workflow_config.yaml):

```yaml
profile_name: tony-dev
bucket_name: sisepuede-data
run_id: "2025-11-12t22;19;28.194097"
```

Meaning of each field:

- `profile_name`: AWS CLI profile used by boto3 to authenticate to S3
- `bucket_name`: S3 bucket holding the SISEPUEDE run outputs
- `run_id`: identifier for the run to train on

The notebook converts `run_id` into an S3 prefix of the form:

```text
transfers/sisepuede_run_<run_id>/
```

For example, with the current config the notebook expects files under:

```text
transfers/sisepuede_run_2025-11-12t22;19;28.194097/
```

## Notebook 1: Data Preparation

Notebook: [`data_prep.ipynb`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/data_prep.ipynb)

### Purpose

This notebook creates the metamodel training table by combining:

- LHS exogenous uncertainty samples
- LHS lever effect samples
- SISEPUEDE model outputs
- cost-benefit output tables
- primary ID metadata used to link `primary_id` back to `future_id` and `design_id`

### Expected Input Files

For the selected `run_id`, the notebook expects these files in the downloaded run directory:

- `ATTRIBUTE_LHC_SAMPLES_EXOGENOUS_UNCERTAINTIES.csv`
- `ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.csv`
- `ATTRIBUTE_PRIMARY.csv`
- `VARIABLE_TRAJECTORY_GROUPS_X.csv`
- `VARIABLE_TRAJECTORY_GROUPS_L.csv`
- `sisepuede_results_IDE_<run_id>.csv`
- `wide_cb_data_lhc_sisepuede_run_<run_id>.csv`

The run is downloaded into:

- [`metamodel/data/ssp`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/data/ssp)

Specifically:

- `metamodel/data/ssp/sisepuede_run_<run_id>/`

If that local directory already exists and is non-empty, the notebook skips the S3 download.

### What the Notebook Does

#### 1. Download the selected run from S3

The notebook:

- reads the AWS profile, bucket, and `run_id` from config
- connects to S3 through `boto3.Session(profile_name=profile_name)`
- downloads files from `transfers/sisepuede_run_<run_id>/`
- skips directory markers and files inside paths containing `transformations`

#### 2. Build predictor features from LHS samples

The notebook loads:

- exogenous uncertainty samples
- lever effect samples

Then it:

- appends `_X` to exogenous sample columns
- appends `_L` to lever sample columns
- preserves `region`, `design_id`, and `future_id` as merge keys
- merges the two tables on `region`, `design_id`, and `future_id`

This creates the raw feature space for the surrogate model.

#### 3. Build emissions targets from SISEPUEDE outputs

From `sisepuede_results_IDE_<run_id>.csv`, the notebook:

- creates `year = time_period + 2015`
- selects columns containing `emission_co2e_subsector_total`
- sums those subsector totals into `emission_total`
- aggregates total emissions by `primary_id`
- computes:
  - `emission_total_sum`
  - `2033_2037_mean_emission`
  - `2066_2070_mean_emission`

These become part of the target set.

#### 4. Build cost-benefit targets

From the wide cost-benefit table, the notebook:

- lowercases column names
- fills null values with zero
- drops `strategy_code` and `future_id`
- groups all non-cost fields into `total_benefits`
- combines `technical_cost` and `system_cost`, multiplies by `-1`, and keeps the result as `technical_cost`
- joins GDP from the SISEPUEDE output file
- computes `technical_cost_relative_to_gdp`

It then aggregates cost-benefit outputs by `primary_id` and computes:

- `2025_2035_mean_benefits`
- `2025_2070_mean_benefits`
- `2025_2035_mean_costs`
- `2025_2070_mean_costs`
- `2025_2035_max_costs_rel_to_gdp`
- `2025_2070_max_costs_rel_to_gdp`
- `2025_2035_cumulative_cost_rel_to_gdp`
- `2025_2070_cumulative_cost_rel_to_gdp`

#### 5. Join targets back to scenario identifiers

The notebook uses `ATTRIBUTE_PRIMARY.csv` to map each `primary_id` back to scenario identifiers and merges:

- emissions aggregates
- cost-benefit aggregates
- primary attributes

This produces one record per `primary_id` with the final target variables attached.

#### 6. Merge features and targets

The notebook merges the LHS feature table with the engineered target table using:

- `design_id`
- `future_id`

Then it:

- moves `future_id` and `primary_id` to the front
- drops `design_id` and `strategy_id`

#### 7. Filter and rename feature columns

The notebook uses:

- `VARIABLE_TRAJECTORY_GROUPS_X.csv`
- `VARIABLE_TRAJECTORY_GROUPS_L.csv`

to decide which LHS columns are relevant.

It keeps only:

- `future_id`
- `primary_id`
- relevant LHS feature groups
- engineered targets

Next, it creates human-readable feature names using the trajectory group metadata. Feature columns are renamed to names like:

- `group_<trajectory_group>_<shared_variable_prefix>`

This is the version used later by the training notebook.

### Data Preparation Outputs

The notebook writes two parquet files to [`metamodel/data/training`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/data/training):

- `training_data_w_suffix_<run_id>.parquet`
- `training_data_<run_id>.parquet`

Use `training_data_w_suffix_<run_id>.parquet` for model training. That is the file referenced in the training notebook.

## Notebook 2: Model Training

Notebook: [`model_training.ipynb`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/model_training.ipynb)

### Purpose

This notebook trains a multi-output XGBoost regression model to predict the engineered metamodel targets from grouped LHS inputs.

### Input

The notebook reads:

- `metamodel/data/training/training_data_w_suffix_<run_id>.parquet`

using the same `run_id` from [`ml_training_workflow_config.yaml`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/config/ml_training_workflow_config.yaml).

### What the Notebook Does

#### 1. Load the training table

It loads the parquet file and drops:

- `primary_id`
- `future_id`

before modeling.

#### 2. Define features and targets

The notebook treats:

- columns starting with `group_` as model features
- all remaining columns as targets

This means the grouped trajectory columns are predictors and the engineered emissions and cost-benefit metrics are outputs.

#### 3. Basic cleaning and EDA

The notebook:

- drops columns that are entirely zero
- checks for `NaN`, `inf`, and `-inf`
- plots histograms of the target variables
- prints feature-target correlations
- inspects outliers using IQR and z-score methods

It then removes outlier rows using `DataCleaningUtils.remove_outliers(..., method="zscore", z_thresh=3.0)`.

This is a simple cleaning step, so users should treat it as a modeling assumption rather than a fixed scientific rule.

#### 4. Train the surrogate model

Training is performed through [`ml_utils_v2.py`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/utils/ml_utils_v2.py), specifically the `XGBMultiOutputPipeline` class.

The notebook currently runs:

```python
mulp = XGBMultiOutputPipeline(df=training_df_cleaned, targets=target_col)
mulp.run(tune=False, log_transform=False, plot_figures=True)
```

Key behavior:

- uses a train/test split
- wraps `xgboost.XGBRegressor` in `sklearn.multioutput.MultiOutputRegressor`
- trains one model for all targets through a shared pipeline interface
- prints test metrics per target:
  - MAE
  - RMSE
  - R2
  - SMAPE
- optionally runs cross-validation
- plots feature importances, residuals, and actual vs predicted figures

At present, hyperparameter tuning is turned off in the notebook with `tune=False`.

#### 5. Test a sample prediction

The notebook predicts one row from the cleaned dataset as a quick sanity check and compares predictions to the original target values.

#### 6. Save the trained model

The trained pipeline is saved under [`metamodel/surrogate_model/trained_models`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/trained_models) as:

- `xgb_pipeline_<run_id>.pkl`

The notebook also reloads that file and runs a prediction again to confirm the saved artifact can be read back.

## Recommended Run Order

For a new run:

1. Update [`ml_training_workflow_config.yaml`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/config/ml_training_workflow_config.yaml) with the correct `profile_name`, `bucket_name`, and `run_id`.
2. Authenticate with AWS SSO using the same `profile_name`.
3. Start Jupyter with the working directory set to [`metamodel/surrogate_model`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model).
4. Run [`data_prep.ipynb`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/data_prep.ipynb) end to end.
5. Confirm the parquet files were created in [`metamodel/data/training`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/data/training).
6. Run [`model_training.ipynb`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/model_training.ipynb) end to end.
7. Confirm the trained model was written to [`metamodel/surrogate_model/trained_models`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/trained_models).

## Common Issues

### AWS authentication fails

Usually this means:

- the AWS SSO session expired
- the configured `profile_name` does not exist locally
- the selected role does not have access to the bucket

Try:

```bash
aws sso login --profile <profile_name>
aws s3 ls s3://<bucket_name>/ --profile <profile_name>
```

### Notebook cannot find files

Check:

- you are running the notebook from [`metamodel/surrogate_model`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model)
- `run_id` in config matches the files in S3
- the expected CSV files exist under `metamodel/data/ssp/sisepuede_run_<run_id>/`

### Parquet read or write errors

Install parquet support such as `pyarrow`.

### Model training errors caused by missing packages

Install any missing dependencies used by the notebooks, especially:

- `xgboost`
- `boto3`
- `joblib`
- `pyarrow`
- `PyYAML`

## Key Outputs

After a successful run, the main artifacts are:

- raw downloaded simulation files in [`metamodel/data/ssp`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/data/ssp)
- engineered training data in [`metamodel/data/training`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/data/training)
- trained surrogate model in [`metamodel/surrogate_model/trained_models`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/trained_models)

## Files Referenced in This Guide

- [`data_prep.ipynb`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/data_prep.ipynb)
- [`model_training.ipynb`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/model_training.ipynb)
- [`ml_training_workflow_config.yaml`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/config/ml_training_workflow_config.yaml)
- [`aws_credentials_config_template.yaml`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/config/aws_credentials_config_template.yaml)
- [`ml_utils_v2.py`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/utils/ml_utils_v2.py)
- [`eda_utils.py`](/Users/tony/Documents/sisepuede_modeling/ssp_uganda_data/metamodel/surrogate_model/utils/eda_utils.py)
