from utils import perform_monte_carlo, plot_histogram, plot_yearly_percentiles, plot_simulations
from helpers import reality_perform_monte_carlo
from flask import Flask, render_template, url_for, request, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import plotly.io as pio
import pandas as pd
import numpy as np
import logging
import redis

pio.renderers.default='browser' #svg

app = Flask(__name__)
app.secret_key = '0311'

# Configure session to use Redis
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis.Redis(host='localhost', port=6379)

# Initialize the session
Session(app)

# Store actual data
actual_data = {}

# Setup logging
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['GET', 'POST'])
def index():
    results = {}
    form_data = session.get('form_data', {})  # Retrieve form_data from session if available
    if request.method == 'POST':
        form_data = request.form.to_dict()

        start = int(request.form['start'])
        end = int(request.form['end'])
        renewable_addition = int(request.form['renewable_addition'])
        current_renewable = int(request.form['current_renewable'])
        current_non_renewable = int(request.form['current_non_renewable'])
        target_renewable = int(request.form['target_renewable'])
        target_non_renewable = int(request.form['target_non_renewable'])

        inputs = {
        'renewable_addition': renewable_addition,
        'start_age': start,
        'end_age': end,
        'renewable': current_renewable,
        'non_renewable': current_non_renewable,
        'target_ren_capacity': target_renewable,
        'target_non_ren_capacity': target_non_renewable,
        'n_simulations': 2000       
        }  

        # Store inputs in session
        session['inputs'] = inputs
        session['form_data'] = form_data

        # Run the Monte Carlo simulation
        mc = perform_monte_carlo(inputs, n=inputs['n_simulations'])
        results = generate_results(mc, inputs)    
        session['results'] = results
        return redirect(url_for('index') + '#results-section')
    results = session.get('results')
    # Remove results from session if present
    #if 'results' in session:
        #session.pop('results')
    return render_template('index.html', results=results, actual_data=actual_data, form_data=form_data)

@app.route('/add_actual', methods=['POST'])
def add_actual():
    results = {}
    if 'inputs' not in session:
        return redirect(url_for('index') + '#section')
    
    if request.method == 'POST':        
        year = int(request.form['year'])
        actual_renewable_addition = request.form.get('actual_renewable_addition', type=int, default=0)
        actual_non_renewable_addition = request.form.get('actual_non_renewable_addition', type=int, default=0)
        actual_renewable_retirement = request.form.get('actual_renewable_retirement', type=int, default=0)
        actual_non_renewable_retirement = request.form.get('actual_non_renewable_retirement', type=int, default=0)

        logging.info(f"Year: {year}")
        logging.info(f"Actual Renewable Addition: {actual_renewable_addition}")
        logging.info(f"Actual Non-Renewable Addition: {actual_non_renewable_addition}")
        logging.info(f"Actual Renewable Retirement: {actual_renewable_retirement}")
        logging.info(f"Actual Non-Renewable Retirement: {actual_non_renewable_retirement}")

        # Retrieve inputs from session
        inputs = session.get('inputs')
        form_data = session.get('form_data', {})
        if not inputs:
            # Handle the case where the inputs are not found in session
            return "No inputs found in session. Please fill in the first form first.", 400

        # Update actual data
        actual_data[year] = {
            'actual_renewable_addition': actual_renewable_addition,
            'actual_non_renewable_addition': actual_non_renewable_addition,
            'actual_renewable_retirement': actual_renewable_retirement,
            'actual_non_renewable_retirement': actual_non_renewable_retirement,
        }

        mc = reality_perform_monte_carlo(inputs, actual_data, n=inputs['n_simulations'])
        results = generate_results(mc, inputs) 
        session['results'] = results
        return redirect(url_for('index') + '#results-section')
    results = session.get('results') 
    # Remove results from session if present
    #if 'results' in session:
        #session.pop('results')
    return render_template('index.html', results=results, actual_data=actual_data, form_data=form_data)

@app.route('/update_actual/<int:year>')
def update_actual(year):
    return redirect(url_for('index') + '#actual')

@app.route('/delete_actual/<int:year>')
def delete_actual(year):
    if year in actual_data:
        del actual_data[year]

    # Retrieve inputs from session
    inputs = session.get('inputs')
    form_data = session.get('form_data', {})
    if inputs:
        # Rerun the Monte Carlo simulation with updated actual_data
        mc = reality_perform_monte_carlo(inputs, actual_data, n=inputs['n_simulations'])
        results = generate_results(mc, inputs)
        session['results'] = results        
        return redirect(url_for('index') + '#results-section')
    results = session.get('results') 
    # Remove results from session if present
    if 'results' in session:
        session.pop('results')
    return render_template('index.html', results=results, actual_data=actual_data, form_data=form_data)

@app.route('/about')
def about():
    return render_template('about.html')

def generate_results(mc, inputs):
    # Generate the plots
    ren_histogram = plot_histogram(mc['renewable'], mc['renewable_upper_confidence'], mc['renewable_lower_confidence'], inputs['target_ren_capacity'], title=f'Renewable Final Capacities') #after {inputs['n_simulations']}
    non_ren_histogram = plot_histogram(mc['non_renewable'], mc['non_renewable_upper_confidence'], mc['non_renewable_lower_confidence'], inputs['target_non_ren_capacity'], title=f'Non-renewable Final Capacities') #after {inputs['n_simulations']}
    ren_percentiles = plot_yearly_percentiles(mc['ren_yearly_percentiles'], inputs['target_ren_capacity'], 'Renewable Capacity Percentiles', renewable=True)
    non_ren_percentiles = plot_yearly_percentiles(mc['non_ren_yearly_percentiles'], inputs['target_non_ren_capacity'], 'Non-renewable Capacity Percentiles', renewable=False)
    #percentiles = plot_yearly_percentiles(mc['ren_yearly_percentiles'], mc['non_ren_yearly_percentiles'], 
     #                                                           title='Renewable & Non-renewable Percentiles after 10000 simulations', 
      #                                                          ylabel='Capacity (MW)', 
       #                                                         ren_target=inputs['target_ren_capacity'], 
        #                                                        ren_target_label='Renewable Target',
         #                                                       non_ren_target=inputs['target_non_ren_capacity'], 
          #                                                      non_ren_target_label='Non-Renewable Target')
    ren_simulations = plot_simulations(mc['ren_cumulatives'], "Renewable Capacity Simulations", "Year", "Capacity (MW)", inputs, increasing=True) 
    non_ren_simulations = plot_simulations(mc['non_ren_cumulatives'], "Non-Renewable Capacity Simulations", "Year", "Capacity (MW)", inputs, increasing=False)

    # Convert the plots to HTML
    ren_histogram_html = pio.to_html(ren_histogram, full_html=False, include_plotlyjs='cdn') 
    non_ren_histogram_html = pio.to_html(non_ren_histogram, full_html=False, include_plotlyjs='cdn')
    ren_percentiles_html = pio.to_html(ren_percentiles, full_html=False, include_plotlyjs='cdn')
    non_ren_percentiles_html = pio.to_html(non_ren_percentiles, full_html=False, include_plotlyjs='cdn')
    #percentiles_html = pio.to_html(percentiles, full_html=False)
    ren_simulations_html = pio.to_html(ren_simulations, full_html=False, include_plotlyjs='cdn')
    non_ren_simulations_html = pio.to_html(non_ren_simulations, full_html=False, include_plotlyjs='cdn')

    # Pass the plot HTML to the template
    return {
        'ren_histogram': ren_histogram_html,
        'non_ren_histogram': non_ren_histogram_html,
        'ren_percentiles': ren_percentiles_html,
        'non_ren_percentiles': non_ren_percentiles_html,
        #'percentiles': percentiles_html,
        'ren_simulations': ren_simulations_html,
        'non_ren_simulations': non_ren_simulations_html,
    } 

if __name__ == "__main__":
    app.run(debug=True)