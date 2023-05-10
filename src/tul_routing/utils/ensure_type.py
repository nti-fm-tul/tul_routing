import enum
from typing import List, Type, TypeVar

import numpy as np

from ..typing import DataFrame, DFStandardisedTypeLike
from .time_utils import parse_entry_timestamp

T = TypeVar('T')
V = TypeVar('V')


def ensure_type(instance: T, desired_type: Type[V]) -> V:
    """
    Given a object T, make sure it is of type V
    :param instance: an object to be checked
    :param desired_type: a type which object is or will be
    :return: either a original object or object converted to type V
    :except: if object cannot be simple cast to type V
    """
    if isinstance(instance, desired_type):
        return instance

    return desired_type(instance)

def ensure_list(instance: T) -> List[T]:
    """
    Given an object T, make sure it is a list
    :param instance: an object to be checked
    :return: either a original object or object converted to list
    :except: if object cannot be simple cast to list
    """

    if isinstance(instance, list):
        return instance
    
    if isinstance(instance, tuple):
        return list(instance)
    
    return [instance]

class CheckOutcome(enum.Enum):
    UNCHANGED = 0
    REPLACED_WITH_OTHER_COLUMN = 1
    NEW_VALUE_COMPUTED = 2
    NEW_COLUMN_CREATED = 3


def check_timestamp_is_valid_dtype(df: DFStandardisedTypeLike, column='timestamp', alt_column='timestamp_unixms'):
    """
    Makes sure the timestamp column, if exists, has a correct format
    If not, will use alt column if applicable or parses the datetime
    Parameters
    ----------
    df
        input dataframe
    column
        timestamp columns name
    alt_column
        column name, which could contain a valid timestamp valus instead

    Returns
    -------

    """
    import numpy as np

    if column in df:
        timestamp_dtype = df.timestamp.dtype

        # we have another column, which can be used
        if not np.issubdtype(timestamp_dtype, np.number) \
                and alt_column in df \
                and np.issubdtype(df[alt_column].dtype, np.number):

            if alt_column in df:
                df[column] = df[alt_column]
                return CheckOutcome.REPLACED_WITH_OTHER_COLUMN
            else:
                # entry csv appears to be in iso format, but not a valid one
                # fractional numbers require 0, 3 or 6 decimal places but we have 7
                # datetime.datetime.fromisoformat thus cannot be used

                df[column] = df[column].map(parse_entry_timestamp)
                return CheckOutcome.NEW_VALUE_COMPUTED
    else:
        # we have another column, which can be used
        if alt_column in df \
                and np.issubdtype(df[alt_column].dtype, np.number):

            if alt_column in df:
                df[column] = df[alt_column]
                return CheckOutcome.NEW_COLUMN_CREATED

    return CheckOutcome.UNCHANGED


def ensure_columns(df: DataFrame, columns: List[str], default=np.nan):
    """Ensures given DataFrame contains given columns or create them

    Args:
        df (DataFrame): target df
        columns (List[str]): list of string if column names
        default ([type], optional): Default value if col does not exists. Defaults to np.nan.

    Returns:
        DataFrame: original DF
    """
    for col in columns:
        if col not in df:
            df[col] = default
    return df


def ensure_mergeable(left: DataFrame, right: DataFrame):
    """
    Alter right DF in a way it can be safely merged. Intersection of left and right columns
    will be { }.
    Parameters
    ----------
    left
    right

    Returns
    -------

    """
    right.drop(left.columns, axis=1, inplace=True, errors='ignore')
    return left, right