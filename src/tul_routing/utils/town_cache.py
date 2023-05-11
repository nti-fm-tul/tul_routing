from ..config import datafiles_file
import pandas as pd

_cols_towns = ['name', 'latitude', 'longitude', 'feature']

class TownCache:
    """
    The class method create() creates new cache instance and loads the towns_df from the file.
    If the towns_df_filename is the same as the one used in the current instance. 
    If it is, it returns the same instance. Otherwise, it creates a new instance.
    """
    current: 'TownCache' = None
    def __init__(self, options: dict):
        self.towns_df_filename = options.get('towns_df_filename', 'towns_eu_reduce.csv')
        self.towns_df = pd.read_csv(datafiles_file(self.towns_df_filename), usecols=_cols_towns)

    @classmethod
    def create(cls, options: dict):
        towns_df_filename = options.get('towns_df_filename', 'towns_eu_reduce.csv')
        if cls.current is not None and cls.current.towns_df_filename == towns_df_filename:
            return cls.current

        cls.current = TownCache(options)
        return cls.current