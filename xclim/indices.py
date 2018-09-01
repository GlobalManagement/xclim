# -*- coding: utf-8 -*-

"""Main module."""
import dask
import numpy as np
import pandas as pd
import xarray as xr

from .checks import *
from . import run_length as rl

# Frequencies : YS: year start, QS-DEC: seasons starting in december, MS: month start
# See http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases
K2C = 273.15





@valid_daily_mean_temperature
def cooling_degree_days(tas, thresh=18, freq='YS'):
    """Cooling degree days above threshold."""
    cdd = (tas > K2C + thresh) * 1
    return cdd.resample(time=freq).sum(dim='time')


@valid_daily_min_temperature
def CFD(tasmin, freq='AS-JUL'):
    """Maximum number of consecutive frost days (Tmin < 0℃)."""

    # TODO: Deal with start and end boundaries
    # TODO: Handle missing values ?
    # TODO: Check that input array has no missing dates (holes)

    # Create an monotonously increasing index [0,1,2,...] along the time dimension.
    i = xr.DataArray(np.arange(tasmin.time.size), dims='time')
    ind = xr.broadcast(i, tasmin)[0]

    # Mask index  values where tasmin > K2C
    d = ind.where(tasmin > K2C)

    # Fill NaNs with the following valid value
    b = d.bfill(dim='time')

    # Find the difference between start and end indices
    d = b.diff(dim='time') - 1

    return d.resample(time=freq).max(dim='time')


@valid_daily_min_temperature
def CFD2(tasmin, freq='AS-JUL'):
    # Results are different from CFD, possibly because resampling occurs at first.
    # CFD looks faster anyway.
    f = tasmin < K2C
    group = f.resample(time=freq)

    def func(x):
        return xr.apply_ufunc(rl.longest_run,
                                x,
                                input_core_dims=[['time'], ],
                                vectorize=True,
                                dask='parallelized',
                                output_dtypes=[np.int, ],
                                keep_attrs=True,
                                )

    return group.apply(func)


@valid_daily_min_temperature
def CSDI(tasmin, freq='YS'):
    """Cold spell duration index."""
    raise NotImplementedError


@valid_daily_mean_temperature
def CSI(tas, thresh=-10, window=5, freq='AS-JUL'):
    """Cold spell index.
    """
    over = tas < K2C + thresh
    group = over.resample(time=freq)

    def func(x):
        xr.apply_ufunc(rl.windowed_run_count,
                        x,
                        input_core_dims=[['time'], ],
                        vectorize=True,
                        dask='parallelized',
                        output_dtypes=[np.int, ],
                        keep_attrs=True,
                        kwargs={'window': window})

    return group.apply(func)


@valid_daily_max_min_temperature
def daily_freezethaw_cycles(tasmax, tasmin, freq='YS'):
    """Number of days with a freeze-thaw cycle.

    The number of days where Tmax > 0℃ and Tmin < 0℃.
    """
    ft = (tasmin < K2C) * (tasmax > K2C) * 1
    return ft.resample(time=freq).sum(dim='time')


@valid_daily_max_min_temperature
def DTR(tasmax, tasmin, freq='YS'):
    """Mean of daily temperature range."""
    dtr = tasmax - tasmin
    return dtr.resample(time=freq).mean(dim='time')


@valid_daily_min_temperature
def FD(tasmin, freq='YS'):
    """Number of frost days (Tmin < 0℃)."""
    f = (tasmin < K2C) * 1
    return f.resample(time=freq).sum(dim='time')


@valid_daily_mean_temperature
def GD4(tas, freq='YS'):
    """Growing degree days over 4℃.

    The sum of degree-days over 4℃.
    """
    thresh = 4 + K2C
    dt = tas.clip(min=thresh) - thresh
    return dt.resample(time=freq).sum(dim='time')


# Work in progress...
@valid_daily_mean_temperature
def GSL(tas):
    """Growing season length.

    The number of days between the first occurrence of at least
    six consecutive days with mean daily temperature over 5C and
    the first occurrence of at least six consecutive days with
    mean daily temperature below 5C after July 1st in the northern
    hemisphere and January 1st in the southern hemisphere.
    """
    freq = 'YS'
    i = xr.DataArray(np.arange(tas.time.size), dims='time')
    ind = xr.broadcast(i, tas)[0]

    c = ((tas > 5 + K2C) * 1).rolling(time=6).sum(dim='time')
    i1 = ind.where(c == 6).resample(time=freq).min(dim='time')

    # Resample sets the time to T00:00.
    i11 = i1.reindex_like(c, method='ffill')

    # TODO: Adjust for southern hemisphere
    i2 = ind.where(c == 0).where(tas.time.dt.month >= 7)
    d = i2 - i11

    return d.resample(time=freq).max(dim='time')


@valid_daily_mean_temperature
def HD(tas, freq='YS', thresh=17):
    """Heating degree days.

    Sum of positive values of threshold - tas.
    """
    hd = (thresh + K2C - tas).clip(0)
    return hd.resample(time=freq).sum(dim='time')


@valid_daily_max_temperature
def hotdays(tasmax, thresh=30, freq='YS'):
    """Number of very hot days.

    The number of days exceeding a threshold. """
    hd = (tasmax > K2C + thresh)*1
    return hd.resample(time=freq).sum(dim='time')


@valid_daily_max_temperature
def HWI(tasmax, thresh=25, window=5, freq='YS'):
    """Heat wave index.

    Number of days that are part of a heatwave, defined as five or more consecutive days over 25℃.

    Parameters
    ----------
    tasmax : xr.DataArray
      Maximum daily temperature.
    thresh : float
      Threshold temperature to designate a heatwave [℃].
    window : int
      Minimum number of days with temperature above threshold to qualify as a heatwave.

    Returns
    -------
    DataArray
      Heat wave index.
    """
    # TODO: Deal better with boundary effects.
    # TODO: Deal with attributes

    over = tasmax > K2C + thresh
    group = over.resample(time=freq)

    def func(x):
        xr.apply_ufunc(rl.windowed_run_count,
                          x,
                          input_core_dims=[['time'],],
                          vectorize=True,
                          dask='parallelized',
                          output_dtypes=[np.int,],
                          keep_attrs=True,
                          kwargs={'window': window})

    return group.apply(func)


@valid_daily_max_temperature
def ID(tasmax, freq='YS'):
    """Number of days where the daily maximum temperature is below 0℃."""
    f = (tasmax < K2C) * 1
    return f.resample(time=freq).sum(dim='time')


@valid_daily_mean_temperature
def TG(tas, freq='YS'):
    r"""Mean of daily mean temperature.

    Resample the original daily mean temperature series by taking the mean over each period.

    Parameters
    ----------
    tas : xarray.DataArray
      Mean daily temperature values [K].
    freq : str, optional
      Resampling frequency.


    Returns
    -------
    xarray.DataArray
      The mean daily temperature at the given time frequency.


    Notes
    -----
    Let :math:`T_i` be the mean daily temperature of day `i`, then for a period `p` starting at
    day `a` and finishing on day `b`

    .. math::

       TG_p = \frac{\sum_{i=a}^{b} T_i}{b - a + 1}


    Examples
    --------
    The following would compute for each grid cell of file `tas.day.nc` the mean temperature
    at the seasonal frequency, ie DJF, MAM, JJA, SON, DJF, etc.

    >>> t = xr.open_dataset('tas.day.nc')
    >>> tg = TG(t, freq="QS-DEC")

    """
    arr = tas.resample(time=freq) if freq else tas
    return arr.mean(dim='time')


@valid_daily_min_temperature
def TN(tasmin, freq='YS'):
    """Mean of daily minimum temperature."""
    arr = tasmin.resample(time=freq) if freq else tasmin
    return arr.mean(dim='time')


# @valid_daily_min_temperature
def TN10p(tasmin, p10, freq='YS'):
    """Days with daily minimum temperature below the 10th percentile of the reference period."""
    return (tasmin.groupby('time.dayofyear') < p10).resample(time=freq).sum(dim='time')


@valid_daily_min_temperature
def TNn(tasmin, freq='YS'):
    """Minimum of daily minimum temperature."""
    return tasmin.resample(time=freq).min(dim='time')


@valid_daily_min_temperature
def TNx(tasmin, freq='YS'):
    """Maximum of daily minimum temperature."""
    return tasmin.resample(time=freq).max(dim='time')


@valid_daily_max_temperature
def TX(tasmax, freq='YS'):
    """Mean of daily maximum temperature."""
    arr = tasmax.resample(time=freq) if freq else tasmax
    return arr.mean(dim='time')


@valid_daily_max_temperature
def TXn(tasmax, freq='YS'):
    """Minimum of daily maximum temperature."""
    return tasmax.resample(time=freq).min(dim='time')


@valid_daily_max_temperature
def TXx(tasmax, freq='YS'):
    """Maximum of daily maximum temperature."""
    return tasmax.resample(time=freq).max(dim='time')


def percentile_doy(arr, window=5, per=.1):
    """Compute the climatological percentile over a moving window
    around the day of the year.
    """
    # TODO: Support percentile array, store percentile in attributes.
    rr = arr.rolling(1, center=True, time=window).construct('window')

    # Create empty percentile array
    g = rr.groupby('time.dayofyear')
    c = g.count(dim=('time', 'window'))

    p = xr.full_like(c, np.nan).astype(float).load()

    for doy, ind in rr.groupby('time.dayofyear'):
        p.loc[{'dayofyear': doy}] = ind.compute().quantile(per, dim=('time', 'window'))

    return p


# TODO: ValueError: argument names set(['enable_cftimeindex']) are not in the set of valid options set(['arithmetic_join', 'display_width'])
# xr.set_options(enable_cftimeindex=False)


def check():
    # Let's try it

    fn = '~/src/flyingpigeon/flyingpigeon/tests/testdata/cmip3/tas.sresb1.giss_model_e_r.run1.atm.da.nc'
    D = xr.open_dataset(fn, chunks={'lat': 1})
    # return TN10p(D.tas, D.tas)
    # return GSL(D.tas)

# o = check()


