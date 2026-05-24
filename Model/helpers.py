import random
import numpy as np
import pandas as pd
from io import BytesIO
import base64
import plotly.io as pio
import plotly.express as px
import plotly.offline as pyo
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from scipy.spatial import cKDTree
import plotly.graph_objects as go
from prophet.plot import plot, plot_components
from utils import (
    get_random_ren_additions, 
    get_random_non_ren_additions, 
    get_random_ren_retirements, 
    get_random_non_ren_retirements, 
    get_confidence_levels, 
    get_yearly_percentiles
)

pio.renderers.default='browser' 

def reality_perform_simulation(inputs: dict, actual_data=None):
    renewable_addition = inputs['renewable_addition']
    renewable = inputs['renewable']
    non_renewable = inputs['non_renewable']
    
    years = inputs['end_age'] - inputs['start_age']
        
    ren_additions = get_random_ren_additions(years=years, ren=renewable_addition)
    non_ren_additions = get_random_non_ren_additions(years=years)
    
    ren_retirements = get_random_ren_retirements(years=years)
    non_ren_retirements = get_random_non_ren_retirements(years=years, ren=renewable_addition)
    
    ren_cumulative = []
    non_ren_cumulative = []
    
    for i in range(years):    
        current_year = inputs['start_age'] + i

        if actual_data and current_year in actual_data:
            actual = actual_data[current_year]
            ren_additions[i] = actual.get('actual_renewable_addition', ren_additions[i])
            non_ren_additions[i] = actual.get('actual_non_renewable_addition', non_ren_additions[i])
            ren_retirements[i] = actual.get('actual_renewable_retirement', ren_retirements[i])
            non_ren_retirements[i] = actual.get('actual_non_renewable_retirement', non_ren_retirements[i])

        renewable += ren_additions[i]
        non_renewable += non_ren_additions[i]
        
        renewable -= ren_retirements[i]
        non_renewable -= non_ren_retirements[i]
        
        ren_cumulative.append(int(renewable))
        non_ren_cumulative.append(int(non_renewable))
        
    return renewable, non_renewable, ren_cumulative, non_ren_cumulative

def reality_perform_monte_carlo(inputs: dict, actual_data=None, n: int = 1000):
    renewable = []
    non_renewable = []
    ren_cumulatives = []
    non_ren_cumulatives = []
    
    for i in range(n):
        final_ren, final_non_ren, ren_cumulative, non_ren_cumulative = reality_perform_simulation(inputs, actual_data)
        renewable.append(final_ren)
        non_renewable.append(final_non_ren)
        ren_cumulatives.append(ren_cumulative)
        non_ren_cumulatives.append(non_ren_cumulative)
        
    renewable_lower_confidence, renewable_upper_confidence = get_confidence_levels(renewable)
    non_renewable_lower_confidence, non_renewable_upper_confidence = get_confidence_levels(non_renewable)
            
    return {
        'renewable': renewable,
        'non_renewable': non_renewable,
        'ren_cumulatives': ren_cumulatives,
        'non_ren_cumulatives': non_ren_cumulatives,
        'renewable_lower_confidence': renewable_lower_confidence,
        'renewable_upper_confidence': renewable_upper_confidence, 
        'non_renewable_lower_confidence': non_renewable_lower_confidence,
        'non_renewable_upper_confidence': non_renewable_upper_confidence, 
        'ren_yearly_percentiles': get_yearly_percentiles(ren_cumulatives, inputs),
        'non_ren_yearly_percentiles': get_yearly_percentiles(non_ren_cumulatives, inputs)
    }
