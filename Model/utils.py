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

pio.renderers.default='browser' 

def plot_simulations(cumulatives, title, xaxis_title, yaxis_title, inputs, increasing=True):

    start_year = inputs['start_age']
    end_year = inputs['end_age']
    target_capacity = inputs['target_ren_capacity'] if increasing else inputs['target_non_ren_capacity']
    years = list(range(start_year + 1, end_year + 1))

    fig = go.Figure()

    for simulation in cumulatives:
        if (increasing and any(capacity >= target_capacity for capacity in simulation)) or \
           (not increasing and any(capacity <= target_capacity for capacity in simulation)):
            line_color = 'green' if increasing else 'green'
        else:
            line_color = '#FF6600'
        
        fig.add_trace(go.Scatter(
            x=years, y=simulation, mode='lines', line=dict(color=line_color, width=0.5), opacity=0.3, name='Capacity'
        ))

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        showlegend=False
    )

    return fig

def plot_histogram(final_capacities: list, 
                   upper_confidence:float, 
                   lower_confidence: float,
                   target_capacity: float,
                   title: str):
    """
    Plots the frequencies of the final capacities.
    """
    median = np.median(final_capacities)

    fig = px.histogram(final_capacities, 
                       title=title)
    
    fig.add_vline(x=lower_confidence, 
                  line_width=3, 
                  line_dash="dash", 
                  line_color="green")
    
    fig.add_vline(x=upper_confidence, 
                  line_width=3, 
                  line_dash="dash", 
                  line_color="green")
    
    fig.add_vline(x=median, 
                  line_width=3, 
                  line_dash="dash", 
                  line_color="black",
                  annotation_font_size=15)
    
    fig.add_vline(x=target_capacity, 
                  line_width=3, 
                  line_dash="dash", 
                  line_color="red")
    
    fig.add_vrect(x0=lower_confidence, 
                  x1=upper_confidence, 
                  line_width=0, 
                  fillcolor="green",
                  opacity=0.2,
                  annotation_text="95% confidence interval",
                  annotation_position="bottom right",
                  annotation_font_size=15)
    
    fig.update_layout(
        xaxis_title="Capacity (MW)",
        yaxis_title="Count",
        showlegend=False,
        font=dict(
            family="Arial",
            size=14
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    if fig.data and len(fig.data) > 0 and fig.data[0].y is not None:
        max_y = max(fig.data[0].y) * 0.95
    else:
        max_y = 0 

    annotations = [
        dict(
            x=median,
            y=max_y,
            xref='x',
            yref='y',
            text='Median',
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-30
        ),
        dict(
            x=target_capacity,
            y=max_y,
            xref='x',
            yref='y',
            text='Target',
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-30
        )
    ]

    fig.update_layout(annotations=annotations)

    return fig

def plot_yearly_percentiles(df, target_capacity, title, renewable=True):
    years = df['year']
    
    fig = go.Figure()

    for col, color, name in zip(['90th_percentile', '75th_percentile', 'median', '25th_percentile', '10th_percentile'],
                                ['blue', 'green', 'red', 'orange', 'purple'],
                                ['90th %tile', '75th %tile', 'Median', '25th %tile', '10th %tile']):
        fig.add_trace(go.Scatter(
            x=years, y=df[col], mode='lines', name=name,
            line=dict(color=color), hoverinfo='x+text', text=[f'{val} ({name})' for val in df[col]]
        ))

    fig.add_trace(go.Scatter(
        x=[years.min(), years.max()], y=[target_capacity, target_capacity], mode='lines', name=f'Target Capacity ({target_capacity})',
        line=dict(color='red', dash='dot'), hoverinfo='skip'
    ))

    for percentile, color in zip(['90th_percentile', '75th_percentile', 'median', '25th_percentile', '10th_percentile'], ['blue', 'green', 'red', 'orange', 'purple']):
        if renewable:
            reach_year = years[df[percentile] >= target_capacity].min()
        else:
            reach_year = years[df[percentile] <= target_capacity].min()
        
        if pd.notna(reach_year):
            fig.add_trace(go.Scatter(
                x=[reach_year, reach_year], y=[0, df[percentile].max()], mode='lines', line=dict(color=color, dash='dash' if renewable else 'dot'), showlegend=False, hoverinfo='skip'
            ))

    fig.update_layout(
        title=title,
        xaxis_title='Year',
        yaxis_title='Capacity (MW)',
        showlegend=True,
        legend=dict(x=1.05, y=0.5, bordercolor="Black", borderwidth=1),
        template='plotly_white'
    )

    fig.update_layout(hovermode='x unified')

    return fig

def get_random_ren_additions(years: int, ren: int, high_weight=0.3, medium_weight=0.5, low_weight=0.2):    
    renewable = []

    for _ in range(years):
        rand_value = random.random()
        
        if rand_value < high_weight:
            renewable.append(random.uniform(ren * 1.25, ren * 1.5)) 
        elif rand_value < high_weight + medium_weight:
            renewable.append(random.uniform(ren * 0.75, ren * 1.25))  
        else:
            renewable.append(random.uniform(ren * 0.4, ren * 0.75))  
    
    return renewable

def get_random_non_ren_additions(years, high_weight=0.1, medium_weight=0.35, low_weight=0.55):
    non_renewable = []
    
    for _ in range(years):
        rand_value = random.random()
        
        if rand_value < high_weight:
            non_renewable.append(random.uniform(40000, 100000))  
        elif rand_value < high_weight + medium_weight:
            non_renewable.append(random.uniform(10000, 40000))  
        else:
            non_renewable.append(random.uniform(0, 10000)) 
    
    return non_renewable

def get_random_ren_retirements(years, high_weight=0.1, medium_weight=0.35, low_weight=0.55):
    renewable = []
    
    for _ in range(years):
        rand_value = random.random()
        
        if rand_value < high_weight:
            renewable.append(random.uniform(40000, 100000))  
        elif rand_value < high_weight + medium_weight:
            renewable.append(random.uniform(10000, 40000))  
        else:
            renewable.append(random.uniform(0, 10000))  
    
    return renewable

def get_random_non_ren_retirements(years: int, ren: int, high_weight=0.1, medium_weight=0.5, low_weight=0.4):    
    non_renewable = []

    for _ in range(years):
        rand_value = random.random()
        
        if rand_value < high_weight:
            non_renewable.append(random.uniform(ren * 1.25, ren * 1.5))  
        elif rand_value < high_weight + medium_weight:
            non_renewable.append(random.uniform(ren * 0.75, ren * 1.25))  
        else:
            non_renewable.append(random.uniform(ren * 0.3, ren * 0.75))  
    
    return non_renewable

def get_confidence_levels(final_capacities):    
    upper_confidence = round(np.quantile(final_capacities, 0.975), 2)
    lower_confidence = round(np.quantile(final_capacities, 0.025), 2)
    
    return lower_confidence, upper_confidence

def get_yearly_percentiles(results, inputs) -> pd.DataFrame:
    """
    Finds the percentiles for each year.
    """
    results_rotated = list(zip(*results[::-1]))

    count = []
    year = []
    ninetieth_percentile = []
    seventy_fifth_percentile = []
    median = []
    twenty_fifth_percentile = []
    tenth_percentile = []
    
    for i, year_results in enumerate(results_rotated):
        new_year = (inputs['start_age'] + 1) + i
        ninetieth_percentile_value = np.percentile(year_results, 90)
        seventy_fifth_percentile_value = np.percentile(year_results, 75)
        median_value = np.median(year_results)
        twenty_fifth_percentile_value = np.percentile(year_results, 25)
        tenth_percentile_value = np.percentile(year_results, 10)
        
        count.append(i + 1)
        year.append(new_year)
        ninetieth_percentile.append(ninetieth_percentile_value)
        seventy_fifth_percentile.append(seventy_fifth_percentile_value)
        median.append(median_value)
        twenty_fifth_percentile.append(twenty_fifth_percentile_value)
        tenth_percentile.append(tenth_percentile_value)
        

    return pd.DataFrame(
        list(
            zip(count,
                year,
                ninetieth_percentile, 
                seventy_fifth_percentile,
                median, 
                twenty_fifth_percentile,
                tenth_percentile)
        ),
        columns=[
            'count',
            'year',
            '90th_percentile',
            '75th_percentile',
            'median', 
            '25th_percentile',
            '10th_percentile']
    )

def perform_simulation(inputs: dict):
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
        renewable += ren_additions[i]
        non_renewable += non_ren_additions[i]
        
        renewable -= ren_retirements[i]
        non_renewable -= non_ren_retirements[i]
        
        ren_cumulative.append(int(renewable))
        non_ren_cumulative.append(int(non_renewable))
        
    return renewable, non_renewable, ren_cumulative, non_ren_cumulative

def perform_monte_carlo(inputs: dict, n: int = 1000):
    renewable = []
    non_renewable = []
    ren_cumulatives = []
    non_ren_cumulatives = []
    
    for i in range(n):
        final_ren, final_non_ren, ren_cumulative, non_ren_cumulative = perform_simulation(inputs)
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
