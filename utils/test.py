import os
import unittest
import pandas as pd

class TestCSVFiles(unittest.TestCase):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(SCRIPT_DIR)
    DATA_DIR = os.path.join(PARENT_DIR, 'output_data')

    @classmethod
    def setUpClass(cls):
        cls.csv_files = [
            os.path.join(cls.DATA_DIR, f) for f in os.listdir(cls.DATA_DIR)
            if f.lower().endswith('.csv')
        ]
        if not cls.csv_files:
            raise FileNotFoundError(f"No .csv files found in {cls.DATA_DIR}")

    def load_csv(self, file):
        try:
            df = pd.read_csv(file, dtype=str, keep_default_na=False, na_values=[''])
            return df
        except Exception as e:
            self.fail(f"Failed to load {file}: {e}")

    def test_year_column_present(self):
        for file in self.csv_files:
            with self.subTest(file=file):
                df = self.load_csv(file)
                self.assertIn('year', df.columns,
                              msg=f"Missing 'year' column in: {file}")

    def test_no_duplicate_years(self):
        for file in self.csv_files:
            with self.subTest(file=file):
                df = self.load_csv(file)
                self.assertIn('year', df.columns,
                              msg=f"Missing 'year' column in: {file}")
                dup_years = df['year'].duplicated(keep=False)
                has_duplicates = dup_years.any()
                self.assertFalse(
                    has_duplicates,
                    msg=f"Duplicated years in 'year' column in: {file}. "
                        f"Duplicated years: {df.loc[dup_years, 'year'].unique()}"
                )

    def test_year_range_complete(self):
        mandatory_years = set(str(y) for y in range(2015, 2101))
        for file in self.csv_files:
            with self.subTest(file=file):
                df = self.load_csv(file)
                self.assertIn('year', df.columns,
                              msg=f"Missing 'year' column in: {file}")
                years_in_file = set(df['year'])
                missing = mandatory_years - years_in_file
                self.assertFalse(
                    missing,
                    msg=f"Missing years {sorted(missing)} in file: {file}"
                )

    def test_no_duplicate_rows(self):
        for file in self.csv_files:
            with self.subTest(file=file):
                df = self.load_csv(file)
                duplicated = df.duplicated(keep=False)
                self.assertFalse(
                    duplicated.any(),
                    msg=f"Completely duplicated rows found in: {file} (indexes: {df.index[duplicated].tolist()})"
                )

    def test_no_missing_values(self):
        for file in self.csv_files:
            with self.subTest(file=file):
                df = self.load_csv(file)
                has_null = df.isnull().any().any()
                # Use .map() per column instead of applymap (no warning!)
                has_blank = (
                    df.apply(lambda col: col.map(lambda x: isinstance(x, str) and x.strip() == "")).any().any()
                )
                self.assertFalse(
                    has_null or has_blank,
                    msg=f"Missing (NaN/blank) values found in: {file}"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
