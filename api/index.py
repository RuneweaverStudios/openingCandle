from flask import Flask, request, jsonify, render_template_string
import json
from datetime import datetime, timedelta

# Try to import optional dependencies
try:
    import yfinance as yf
    import pandas as pd
    import pytz
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

app = Flask(__name__)

# HTML template for the main page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MNQ Futures Charts</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1a1a1a;
            color: #ffffff;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
        }

        .controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        label {
            font-size: 14px;
            color: #cccccc;
        }

        input, button {
            padding: 8px 12px;
            border: 1px solid #444;
            background-color: #2a2a2a;
            color: #ffffff;
            border-radius: 4px;
        }

        button {
            background-color: #0066cc;
            cursor: pointer;
            font-weight: bold;
        }

        button:hover {
            background-color: #0052a3;
        }

        button:disabled {
            background-color: #666;
            cursor: not-allowed;
        }

        #exportBtn {
            background-color: #28a745;
        }

        #exportBtn:hover {
            background-color: #218838;
        }

        .export-container {
            margin-top: 20px;
            padding: 20px;
            background-color: #2a2a2a;
            border-radius: 8px;
            text-align: center;
        }

        .error {
            color: #ff6b6b;
            text-align: center;
            margin: 20px 0;
        }

        .charts-container {
            display: grid;
            grid-template-columns: 1fr;
            gap: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }

        .chart-section {
            background-color: #2a2a2a;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        .chart-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #ffffff;
        }

        .chart {
            height: 400px;
        }

        .range-info {
            margin-bottom: 15px;
            padding: 10px;
            background-color: #1a1a1a;
            border-radius: 4px;
            font-size: 14px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .range-box {
            padding: 8px;
            border-radius: 4px;
        }

        .range-box label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: #ffffff;
            cursor: pointer;
            margin-bottom: 4px;
        }

        .range-box input[type="checkbox"] {
            margin: 0;
            transform: scale(1.2);
            accent-color: #0066cc;
        }

        .range-5min {
            border-left: 4px solid #3498db;
            background-color: rgba(52, 152, 219, 0.1);
        }

        .range-15min {
            border-left: 4px solid #27ae60;
            background-color: rgba(39, 174, 96, 0.1);
        }

        .range-first {
            border-left: 4px solid #e74c3c;
            background-color: rgba(231, 76, 60, 0.1);
        }

        .loading {
            text-align: center;
            color: #ffffff;
            font-size: 16px;
        }

        @media (max-width: 768px) {
            .charts-container {
                grid-template-columns: 1fr;
            }

            .range-info {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 MNQ Futures Charts</h1>
        <p>Micro Nasdaq Futures - Multi-Timeframe Analysis with Range Markers</p>
    </div>

    <div class="controls">
        <div class="control-group">
            <label for="date">Trading Date:</label>
            <input type="date" id="date">
        </div>

        <button onclick="generateCharts()" id="generateBtn">Generate Charts</button>
        <button onclick="exportAllCharts()" id="exportBtn">Export All Charts</button>
    </div>

    <div id="error" class="error" style="display: none;"></div>
    <div id="loading" class="loading" style="display: none;">Loading charts...</div>

    <div class="charts-container">
        <div class="chart-section">
            <div class="chart-title">30-Second Chart</div>
            <div class="range-info">
                <div class="range-box range-first">
                    <label>
                        <input type="checkbox" id="showFirst-30s" checked> First 30s Candle Range:
                    </label>
                    <span id="rangeFirst-30s">-</span>
                </div>
                <div class="range-box range-5min">
                    <label>
                        <input type="checkbox" id="show5min-30s"> First 5min Range:
                    </label>
                    <span id="range5min-30s">-</span>
                </div>
                <div class="range-box range-15min">
                    <label>
                        <input type="checkbox" id="show15min-30s"> First 15min Range:
                    </label>
                    <span id="range15min-30s">-</span>
                </div>
            </div>
            <div id="chart30s" class="chart"></div>
        </div>

        <div class="chart-section">
            <div class="chart-title">5-Minute Chart</div>
            <div class="range-info">
                <div class="range-box range-first">
                    <label>
                        <input type="checkbox" id="showFirst-5m"> First 30s Candle Range:
                    </label>
                    <span id="rangeFirst-5m">-</span>
                </div>
                <div class="range-box range-5min">
                    <label>
                        <input type="checkbox" id="show5min-5m" checked> First 5min Range:
                    </label>
                    <span id="range5min-5m">-</span>
                </div>
                <div class="range-box range-15min">
                    <label>
                        <input type="checkbox" id="show15min-5m"> First 15min Range:
                    </label>
                    <span id="range15min-5m">-</span>
                </div>
            </div>
            <div id="chart5m" class="chart"></div>
        </div>

        <div class="chart-section">
            <div class="chart-title">15-Minute Chart</div>
            <div class="range-info">
                <div class="range-box range-first">
                    <label>
                        <input type="checkbox" id="showFirst-15m"> First 30s Candle Range:
                    </label>
                    <span id="rangeFirst-15m">-</span>
                </div>
                <div class="range-box range-5min">
                    <label>
                        <input type="checkbox" id="show5min-15m"> First 5min Range:
                    </label>
                    <span id="range5min-15m">-</span>
                </div>
                <div class="range-box range-15min">
                    <label>
                        <input type="checkbox" id="show15min-15m" checked> First 15min Range:
                    </label>
                    <span id="range15min-15m">-</span>
                </div>
            </div>
            <div id="chart15m" class="chart"></div>
        </div>
    </div>

    <script>
        // Set most recent trading day as default
        function setDefaultDate() {
            const pacific = new Date();
            const utc = pacific.getTime() + pacific.getTimezoneOffset() * 60000;
            const pacificTime = new Date(utc - 480 * 60000); // UTC-8 for Pacific
            const dayOfWeek = pacificTime.getDay();

            // If it's evening in Pacific (after market close), use today
            // If it's morning before market close or weekend, use last trading day
            let targetDate = new Date(pacificTime);

            // If weekend, go back to Friday
            if (dayOfWeek === 0) { // Sunday
                targetDate.setDate(targetDate.getDate() - 2);
            } else if (dayOfWeek === 6) { // Saturday
                targetDate.setDate(targetDate.getDate() - 1);
            }

            // If it's Sunday evening after 6 PM PT, it might show Monday
            // Let's check if the date is in the future and adjust if needed
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            targetDate.setHours(0, 0, 0, 0);

            if (targetDate > today) {
                // If the calculated date is in the future, use today
                targetDate = today;
                // If today is weekend, go back to Friday
                const todayDayOfWeek = targetDate.getDay();
                if (todayDayOfWeek === 0) { // Sunday
                    targetDate.setDate(targetDate.getDate() - 2);
                } else if (todayDayOfWeek === 6) { // Saturday
                    targetDate.setDate(targetDate.getDate() - 1);
                }
            }

            document.getElementById('date').value = targetDate.toISOString().split('T')[0];
        }

        // Generate charts
        async function generateCharts() {
            const date = document.getElementById('date').value;

            if (!date) {
                showError('Please select a date');
                return;
            }

            hideError();
            showLoading(true);
            document.getElementById('generateBtn').disabled = true;

            try {
                const response = await fetch(`/api/mnq-data?date=${date}`);

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to fetch data');
                }

                const data = await response.json();

                // Store chart data globally for toggle listeners
                window.currentChartData = data.data;

                // Calculate ranges
                const ranges = calculateRanges(data.data);

                // Create charts
                createChart('chart30s', data.data['30s'], ranges, '30s');
                createChart('chart5m', data.data['5m'], ranges, '5m');
                createChart('chart15m', data.data['15m'], ranges, '15m');

                // Update range info
                updateRangeInfo(ranges);

            } catch (error) {
                showError(`Error: ${error.message}`);
            } finally {
                showLoading(false);
                document.getElementById('generateBtn').disabled = false;
            }
        }

        function calculateRanges(data) {
            console.log('=== DEBUG: calculateRanges called ===');
            console.log('30s data length:', data['30s']?.length || 0);
            console.log('5m data length:', data['5m']?.length || 0);
            console.log('15m data length:', data['15m']?.length || 0);

            // Find first 5min and 15min candles
            const first5min = data['5m'][0];
            const first15min = data['15m'][0];

            console.log('First 5min candle:', first5min);
            console.log('First 15min candle:', first15min);

            // Calculate first 30-second candle range (just the first candle)
            let first30sRange = { high: 0, low: 0, range: '0' };
            if (data['30s'] && data['30s'].length >= 1) {
                const firstCandle = data['30s'][0];
                first30sRange.high = firstCandle.high;
                first30sRange.low = firstCandle.low;
                first30sRange.range = (first30sRange.high - first30sRange.low).toFixed(2);
                console.log('First 30s candle:', firstCandle);
                console.log('First 30s range:', first30sRange);
            }

            // Calculate first 5min range from 30-second data (10 candles = 5 minutes)
            let first5minRange = { high: 0, low: 0, range: '0' };
            if (data['30s'] && data['30s'].length >= 10) {
                // Get first 10 thirty-second candles (5 minutes)
                const first10ThirtySec = data['30s'].slice(0, 10);
                console.log('First 10 thirty-second candles:', first10ThirtySec);

                first5minRange.high = Math.max(...first10ThirtySec.map(c => c.high));
                first5minRange.low = Math.min(...first10ThirtySec.map(c => c.low));
                first5minRange.range = (first5minRange.high - first5minRange.low).toFixed(2);

                console.log('Calculated 5min range:', first5minRange);
            } else {
                console.log('Not enough 30s data for 5min range. Available:', data['30s']?.length || 0);
            }

            // Calculate first 15min range from 30-second data (30 candles = 15 minutes)
            let first15minRange = { high: 0, low: 0, range: '0' };
            if (data['30s'] && data['30s'].length >= 30) {
                // Get first 30 thirty-second candles (15 minutes)
                const first30ThirtySec = data['30s'].slice(0, 30);
                console.log('First 30 thirty-second candles count:', first30ThirtySec.length);

                first15minRange.high = Math.max(...first30ThirtySec.map(c => c.high));
                first15minRange.low = Math.min(...first30ThirtySec.map(c => c.low));
                first15minRange.range = (first15minRange.high - first15minRange.low).toFixed(2);

                console.log('Calculated 15min range:', first15minRange);
            } else {
                console.log('Not enough 30s data for 15min range. Available:', data['30s']?.length || 0);
            }

            const result = {
                'first': first30sRange,
                '5min': first5minRange,
                '15min': first15minRange
            };

            console.log('Final result:', result);
            console.log('=== END DEBUG ===');

            return result;
        }

        function createChart(elementId, candleData, ranges, timeframe) {
            if (!candleData || candleData.length === 0) {
                document.getElementById(elementId).innerHTML = '<div style="text-align: center; padding: 50px;">No data available</div>';
                return;
            }

            // Convert timestamps to Pacific time for display
            const times = candleData.map(c => {
                // Parse the timestamp - it should already be in Pacific time from the backend
                const date = new Date(c.timestamp);
                return date;
            });
            const opens = candleData.map(c => c.open);
            const highs = candleData.map(c => c.high);
            const lows = candleData.map(c => c.low);
            const closes = candleData.map(c => c.close);

            const trace = {
                x: times,
                open: opens,
                high: highs,
                low: lows,
                close: closes,
                type: 'candlestick',
                name: 'MNQ',
                increasing: {line: {color: '#00ff00'}},
                decreasing: {line: {color: '#ff0000'}}
            };

            // Add range lines based on toggle states
            const shapes = [];
            const annotations = [];

            // Check toggle states for this specific chart
            const showFirst = document.getElementById(`showFirst-${timeframe}`)?.checked ?? true;
            const show5min = document.getElementById(`show5min-${timeframe}`)?.checked ?? true;
            const show15min = document.getElementById(`show15min-${timeframe}`)?.checked ?? true;

            // First 30s candle range (red) - show across the entire chart
            if (showFirst && ranges['first'].high > 0) {
                shapes.push(
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1], // Show across entire chart
                        y0: ranges['first'].high,
                        y1: ranges['first'].high,
                        line: {color: '#e74c3c', width: 3, dash: 'solid'}
                    },
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1], // Show across entire chart
                        y0: ranges['first'].low,
                        y1: ranges['first'].low,
                        line: {color: '#e74c3c', width: 3, dash: 'solid'}
                    }
                );
                // Left side annotation
                annotations.push({
                    x: 0.02,
                    y: 0.98,
                    xref: 'paper',
                    yref: 'paper',
                    text: `First 30s: ${ranges['first'].low}-${ranges['first'].high}`,
                    showarrow: false,
                    font: {color: '#e74c3c', size: 10, weight: 'bold'},
                    xanchor: 'left',
                    yanchor: 'top'
                });
                  }

            // 5min range (blue)
            if (show5min && ranges['5min'].high > 0) {
                shapes.push(
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: ranges['5min'].high,
                        y1: ranges['5min'].high,
                        line: {color: '#3498db', width: 2, dash: 'dash'}
                    },
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: ranges['5min'].low,
                        y1: ranges['5min'].low,
                        line: {color: '#3498db', width: 2, dash: 'dash'}
                    }
                );
                // Left side annotation for 5min
                annotations.push({
                    x: 0.02,
                    y: showFirst ? 0.92 : 0.98, // Adjust position based on first candle visibility
                    xref: 'paper',
                    yref: 'paper',
                    text: `5min: ${ranges['5min'].low}-${ranges['5min'].high}`,
                    showarrow: false,
                    font: {color: '#3498db', size: 10},
                    xanchor: 'left',
                    yanchor: 'top'
                });
                }

            // 15min range (green)
            if (show15min && ranges['15min'].high > 0) {
                shapes.push(
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: ranges['15min'].high,
                        y1: ranges['15min'].high,
                        line: {color: '#27ae60', width: 2, dash: 'dash'}
                    },
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: ranges['15min'].low,
                        y1: ranges['15min'].low,
                        line: {color: '#27ae60', width: 2, dash: 'dash'}
                    }
                );
                const yPosition = showFirst ? 0.86 : (show5min ? 0.92 : 0.98); // Adjust position based on visibility
                // Left side annotation for 15min
                annotations.push({
                    x: 0.02,
                    y: yPosition,
                    xref: 'paper',
                    yref: 'paper',
                    text: `15min: ${ranges['15min'].low}-${ranges['15min'].high}`,
                    showarrow: false,
                    font: {color: '#27ae60', size: 10},
                    xanchor: 'left',
                    yanchor: 'top'
                });
                  }

            const layout = {
                title: `MNQ Futures - ${timeframe.toUpperCase()} (${document.getElementById('date').value || new Date().toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'})} PT)`,
                titlefont: {color: '#ffffff', size: 14},
                paper_bgcolor: '#2a2a2a',
                plot_bgcolor: '#1a1a1a',
                font: {color: '#ffffff'},
                xaxis: {
                    rangeslider: {visible: false},
                    gridcolor: '#444',
                    type: 'date',
                    tickformat: '%H:%M', // Show time in HH:MM format
                    tickfont: {color: '#ffffff', size: 9},
                    showgrid: true,
                    dtick: 3600000, // Tick every hour
                    tick0: '06:30' // Start at 6:30 AM
                },
                yaxis: {
                    gridcolor: '#444',
                    tickfont: {color: '#ffffff', size: 10},
                    autorange: true
                },
                margin: {t: 50, r: 20, b: 60, l: 70}, // Increased top margin for title
                shapes: shapes,
                annotations: annotations
            };

            const config = {
                responsive: true,
                displayModeBar: false
            };

            Plotly.newPlot(elementId, [trace], layout, config);
        }

        function updateRangeInfo(ranges) {
            // Update all range displays
            const rangeFirstText = `${ranges['first'].low} - ${ranges['first'].high} (Range: ${ranges['first'].range})`;
            const range5minText = `${ranges['5min'].low} - ${ranges['5min'].high} (Range: ${ranges['5min'].range})`;
            const range15minText = `${ranges['15min'].low} - ${ranges['15min'].high} (Range: ${ranges['15min'].range})`;

            // Update 30s chart
            document.getElementById('rangeFirst-30s').textContent = rangeFirstText;
            document.getElementById('range5min-30s').textContent = range5minText;
            document.getElementById('range15min-30s').textContent = range15minText;

            // Update 5m chart
            document.getElementById('rangeFirst-5m').textContent = rangeFirstText;
            document.getElementById('range5min-5m').textContent = range5minText;
            document.getElementById('range15min-5m').textContent = range15minText;

            // Update 15m chart
            document.getElementById('rangeFirst-15m').textContent = rangeFirstText;
            document.getElementById('range5min-15m').textContent = range5minText;
            document.getElementById('range15min-15m').textContent = range15minText;
        }

        // Export all charts as images
        async function exportAllCharts() {
            const date = document.getElementById('date').value || 'unknown';
            const ticker = 'MNQ';

            try {
                // Create a combined container
                const exportContainer = document.createElement('div');
                exportContainer.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: white;
                    z-index: 9999;
                    padding: 20px;
                    overflow-y: auto;
                `;

                // Add title and date
                const header = document.createElement('div');
                header.innerHTML = `
                    <h1 style="color: #333; text-align: center; margin-bottom: 10px;">
                        ${ticker} Futures Charts - ${date}
                    </h1>
                    <p style="color: #666; text-align: center; margin-bottom: 30px;">
                        <strong>First 5min Range:</strong> ${document.getElementById('range5min-30s').textContent} |
                        <strong>First 15min Range:</strong> ${document.getElementById('range15min-30s').textContent}
                    </p>
                `;
                exportContainer.appendChild(header);

                // Get all three charts
                const chartIds = ['chart30s', 'chart5m', 'chart15m'];
                const titles = ['30-Second Chart', '5-Minute Chart', '15-Minute Chart'];

                for (let i = 0; i < chartIds.length; i++) {
                    const chartElement = document.getElementById(chartIds[i]);
                    const chartSection = document.createElement('div');
                    chartSection.style.cssText = 'margin-bottom: 40px; background: white; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;';

                    // Add chart title
                    const chartTitle = document.createElement('h3');
                    chartTitle.textContent = titles[i];
                    chartTitle.style.cssText = 'color: #333; text-align: center; margin: 15px 0; font-size: 18px;';
                    chartSection.appendChild(chartTitle);

                    // Clone the chart
                    const chartClone = chartElement.cloneNode(true);
                    chartClone.style.cssText = 'height: 400px; width: 100%; background: white;';
                    chartSection.appendChild(chartClone);

                    exportContainer.appendChild(chartSection);
                }

                // Add export instructions
                const instructions = document.createElement('div');
                instructions.innerHTML = `
                    <p style="color: #666; text-align: center; margin-top: 30px;">
                        Use your browser's print function (Cmd+P or Ctrl+P) to save as PDF, or take screenshots
                    </p>
                    <button onclick="this.parentElement.parentElement.remove()" style="
                        display: block;
                        margin: 20px auto;
                        padding: 10px 20px;
                        background: #dc3545;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 16px;
                    ">Close Export View</button>
                `;
                exportContainer.appendChild(instructions);

                document.body.appendChild(exportContainer);

                // Redraw charts in the new container
                for (let i = 0; i < chartIds.length; i++) {
                    const chartClone = exportContainer.querySelectorAll('.plotly')[i];
                    if (window.Plotly && chartClone) {
                        // This will require re-plotting with white background
                        // For now, the clone should work for screenshots
                    }
                }

            } catch (error) {
                showError('Export failed: ' + error.message);
            }
        }

        function showError(message) {
            const errorEl = document.getElementById('error');
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }

        function hideError() {
            document.getElementById('error').style.display = 'none';
        }

        function showLoading(show) {
            document.getElementById('loading').style.display = show ? 'block' : 'none';
        }

        // Add event listeners for checkboxes
        function addToggleListeners() {
            const timeframes = ['30s', '5m', '15m'];
            const ranges = ['First', '5min', '15min'];

            timeframes.forEach(timeframe => {
                ranges.forEach(range => {
                    const checkbox = document.getElementById(`show${range}-${timeframe}`);
                    if (checkbox) {
                        checkbox.addEventListener('change', () => {
                            // Re-create chart when toggle changes
                            const chartData = window.currentChartData;
                            if (chartData) {
                                const currentRanges = calculateRanges(chartData);
                                createChart(`chart${timeframe}`, chartData[timeframe], currentRanges, timeframe);
                            }
                        });
                    }
                });
            });
        }

        // Initialize
        setDefaultDate();
        addToggleListeners();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    """Serve the main HTML page"""
    return render_template_string(HTML_TEMPLATE)

def get_market_data(target_date):
    """Fetch MNQ futures data from Yahoo Finance"""
    if not DEPENDENCIES_AVAILABLE:
        return {
            'error': 'Dependencies not available',
            'message': 'yfinance, pandas, or pytz not installed',
            'data': {'30s': [], '5m': [], '15m': []}
        }

    try:
        pacific = pytz.timezone('America/Los_Angeles')

        ticker = yf.Ticker("MNQ=F")
        end_date = target_date + timedelta(days=1)
        start_date = target_date

        data = ticker.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval='1m',
            prepost=True
        )

        if data.empty:
            return {
                'error': 'No data available',
                'message': 'Yahoo Finance typically only provides intraday data for the last 7 days.',
                'data': {'30s': [], '5m': [], '15m': []}
            }

        data.index = data.index.tz_convert('America/Los_Angeles')
        market_data = data.between_time('06:30', '13:00')

        if market_data.empty:
            market_data = data

        df = pd.DataFrame({
            'timestamp': market_data.index,
            'open': market_data['Open'],
            'high': market_data['High'],
            'low': market_data['Low'],
            'close': market_data['Close'],
            'volume': market_data['Volume']
        })

        df = df.reset_index(drop=True)

        thirty_sec_data = process_timeframe(df, 0.5)
        five_min_data = process_timeframe(df, 5)
        fifteen_min_data = process_timeframe(df, 15)

        return {
            'success': True,
            'data': {
                '30s': thirty_sec_data,
                '5m': five_min_data,
                '15m': fifteen_min_data
            }
        }

    except Exception as e:
        return {
            'error': 'Data fetch failed',
            'message': str(e),
            'data': {'30s': [], '5m': [], '15m': []}
        }

def process_timeframe(df, minutes):
    """Resample data to specified timeframe"""
    if not DEPENDENCIES_AVAILABLE:
        return []

    if minutes == 0.5:
        return create_30second_data(df)

    if minutes == 1:
        result = df.to_dict('records')
        # Convert pandas timestamps to ISO format
        for record in result:
            if 'timestamp' in record:
                record['timestamp'] = pd.Timestamp(record['timestamp']).isoformat()
        return result

    df_temp = df.set_index('timestamp')
    # Fixed deprecation warning
    df_resampled = df_temp.resample(f'{minutes}min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    result = df_resampled.reset_index().to_dict('records')
    # Convert pandas timestamps to ISO format
    for record in result:
        if 'timestamp' in record:
            record['timestamp'] = pd.Timestamp(record['timestamp']).isoformat()
    return result

def create_30second_data(df):
    """Create synthetic 30-second candles from 1-minute data"""
    if not DEPENDENCIES_AVAILABLE or df.empty:
        return []

    candles_30s = []

    for _, row in df.iterrows():
        timestamp = row['timestamp']
        o = row['open']
        h = row['high']
        l = row['low']
        c = row['close']
        v = row['volume']

        mid_price = (o + h + l + c) / 4

        candles_30s.append({
            'timestamp': pd.Timestamp(timestamp).isoformat(),
            'open': float(o),
            'high': float(max(h, mid_price)),
            'low': float(min(l, mid_price)),
            'close': float(mid_price),
            'volume': int(v // 2)
        })

        second_timestamp = pd.Timestamp(timestamp) + pd.Timedelta(seconds=30)

        candles_30s.append({
            'timestamp': second_timestamp.isoformat(),
            'open': float(mid_price),
            'high': float(max(h, mid_price)),
            'low': float(min(l, mid_price)),
            'close': float(c),
            'volume': int(v // 2)
        })

    return candles_30s

@app.route('/api/test', methods=['GET'])
def test():
    """Test endpoint with full yfinance functionality"""
    return jsonify({
        'status': 'success',
        'message': 'Serverless function is working with full functionality!',
        'dependencies_available': DEPENDENCIES_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/mnq-data', methods=['GET'])
def get_mnq_data():
    """Fetch MNQ futures data from Yahoo Finance"""
    try:
        date_param = request.args.get('date')

        pacific = pytz.timezone('America/Los_Angeles') if DEPENDENCIES_AVAILABLE else None

        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'error': 'Invalid date format',
                    'message': 'Use YYYY-MM-DD format'
                }), 400
        else:
            if DEPENDENCIES_AVAILABLE and pacific:
                target_date = datetime.now(pacific).date()
                if target_date.weekday() >= 5:
                    target_date = target_date - timedelta(days=target_date.weekday() - 4)
            else:
                target_date = datetime.now().date()

        market_data_result = get_market_data(target_date)

        if market_data_result.get('error'):
            return jsonify({
                'error': market_data_result['error'],
                'message': market_data_result['message'],
                'date': target_date.strftime('%Y-%m-%d'),
                'data': market_data_result['data']
            }), 404

        result = {
            'date': target_date.strftime('%Y-%m-%d'),
            'market_hours': {
                'open': '06:30:00',
                'close': '13:00:00',
                'timezone': 'America/Los_Angeles'
            },
            'data': market_data_result['data']
        }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'data': {'30s': [], '5m': [], '15m': []}
        }), 500

# Vercel serverless handler for builds system
def handler(environ, start_response):
    return app(environ, start_response)

if __name__ == '__main__':
    app.run(debug=True, port=5001)