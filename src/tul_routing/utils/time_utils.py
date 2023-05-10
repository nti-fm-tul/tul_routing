from datetime import datetime


def parse_entry_timestamp(data: str):
    """
    Parses entry timestamp something like '2021-05-31T04:22:41.3838876'
    to unix ms timestamp
    
    Parameters
    ----------
    data

    Returns
    -------

    """
    part = str(data).split("+")[0]
    return int(datetime.strptime(part[:26], '%Y-%m-%dT%H:%M:%S.%f').timestamp() * 1000)
