from statsmodels.compat.pandas import MONTH_END

import pandas as pd
import pytest
import tempfile
import os

from statsmodels.datasets import co2, macrodata
from statsmodels.tsa.x13 import (
    _find_x12,
    x13_arima_analysis,
    x13_arima_select_order,
)

x13path = _find_x12()

pytestmark = pytest.mark.skipif(x13path is False,
                                reason='X13/X12 not available')

dta = macrodata.load_pandas().data
index = pd.period_range(start='1959Q1', end='2009Q3', freq='Q')
dta.index = index
quarterly_data = dta.dropna()

dta = co2.load_pandas().data
dta['co2'] = dta.co2.interpolate()
monthly_data = dta.resample(MONTH_END)
# change in pandas 0.18 resample is deferred object
if not isinstance(monthly_data, (pd.DataFrame, pd.Series)):
    monthly_data = monthly_data.mean()

monthly_start_data = dta.resample('MS')
if not isinstance(monthly_start_data, (pd.DataFrame, pd.Series)):
    monthly_start_data = monthly_start_data.mean()

data = (monthly_data, monthly_start_data, monthly_data.co2,
        monthly_start_data.co2, quarterly_data.realgdp,
        quarterly_data[['realgdp']])
ids = ('monthly', 'monthly_start', 'monthly_co2', 'monthly_start_co2',
       'series', 'dataframe')


@pytest.fixture(params=data, ids=ids)
def dataset(request):
    return request.param


def test_x13_arima_select_order(dataset):
    res = x13_arima_select_order(dataset)
    assert isinstance(res.order, tuple)
    assert isinstance(res.sorder, tuple)


@pytest.mark.matplotlib
def test_x13_arima_plot(dataset):
    res = x13_arima_analysis(dataset)
    res.plot()


def test_x13_arima_rawspec_arg():
    with pytest.raises(ValueError):
        # error because both param and rawspec are specified
        x13_arima_analysis(dataset, outlier=True, rawspec="/fake/path.spc")

    with pytest.raises(ValueError):
        # error because of fake path
        x13_arima_analysis(dataset, rawspec="/fake/path.spc")


def test_x13_arima_rawspec_run(dataset):
    # example rawspec file string
    raw_spec_file = """
series { 
    modelspan=(,) 
    save=(B1) 
    span=(,) 
    type=(flow) 
}
x11 { 
    seasonalma=(  msr) 
    appendfcst=yes 
    mode=(mult) 
    print=( seasadj seasonal adjustfac) 
    save=(seasadj seasonal adjustfac) 
    savelog=(  alldiagnostics) 
} 
arima {model=(0 1 0)(1 0 1)} 
transform { 
    function=log 
} 
regression { 
    savelog=(  aictest) 
 } 
estimate {save=mdl} 
slidingspans { } 
history { 
    estimates=(sadj seasonal fcst) 
    fixmdl=yes
}
"""

    # pass rawspec as string
    x13_arima_analysis(dataset, rawspec=raw_spec_file)

    # pass rawspec as file path
    with tempfile.NamedTemporaryFile(suffix='.spc') as ft:
        ft.write(raw_spec_file.encode('utf8'))
        ft.seek(0)

        x13_arima_analysis(dataset, rawspec=ft.name)