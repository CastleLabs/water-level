// Water Monitor Dashboard JavaScript

let chart = null;
let currentTimeframe = 24;
// Store system settings fetched from the server
let systemSettings = { leak_threshold: 5.0 };

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    updateCurrent();
    updateStatistics();
    loadAlerts();
    loadChart(24);

    // Set up periodic updates
    setInterval(updateCurrent, 30000);  // Update current readings every 30 seconds
    setInterval(updateStatistics, 60000);  // Update stats every minute
    setInterval(loadAlerts, 60000);  // Check alerts every minute
});

// Fetch settings from the server to use for UI logic
function loadSettings() {
    fetch('/api/settings')
        .then(response => response.json())
        .then(settings => {
            if (settings && settings.leak_threshold) {
                systemSettings = settings;
            }
        })
        .catch(error => console.error('Error fetching settings:', error));
}

// Update current readings
function updateCurrent() {
    fetch('/api/current')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error fetching current readings:', data.error);
                return;
            }

            // Update reference sensor
            document.getElementById('reference-level').textContent =
                data.reference?.percentage?.toFixed(1) || '--';
            document.getElementById('reference-raw').textContent =
                data.reference?.raw || '--';

            // Update control sensor
            document.getElementById('control-level').textContent =
                data.control?.percentage?.toFixed(1) || '--';
            document.getElementById('control-raw').textContent =
                data.control?.raw || '--';

            // Update difference
            const difference = data.difference || 0;
            document.getElementById('difference').textContent =
                Math.abs(difference).toFixed(1);

            // Update status and styling
            const diffBox = document.getElementById('difference-box');
            const status = document.getElementById('status');

            // Use the configurable threshold from settings, not a hardcoded value
            if (Math.abs(difference) > systemSettings.leak_threshold) {
                diffBox.classList.add('leak');
                status.textContent = 'LEAK DETECTED';
                status.style.color = '#ff6b6b';
            } else {
                diffBox.classList.remove('leak');
                status.textContent = 'Normal';
                status.style.color = '#48c774';
            }

            // Update timestamp
            document.getElementById('last-update').textContent =
                new Date().toLocaleTimeString();
        })
        .catch(error => console.error('Error:', error));
}

// Update statistics
function updateStatistics() {
    fetch('/api/statistics/24')
        .then(response => response.json())
        .then(data => {
            document.getElementById('avg-reference').textContent =
                data.avg_reference?.toFixed(1) || '--';
            document.getElementById('avg-control').textContent =
                data.avg_control?.toFixed(1) || '--';
            document.getElementById('max-difference').textContent =
                data.max_difference?.toFixed(1) || '--';
            document.getElementById('reading-count').textContent =
                data.reading_count || '--';
        })
        .catch(error => console.error('Error loading statistics:', error));
}

// Load and display alerts
function loadAlerts() {
    fetch('/api/alerts')
        .then(response => response.json())
        .then(alerts => {
            const alertsContainer = document.getElementById('alerts');
            alertsContainer.innerHTML = '';

            if (alerts.length === 0) return;

            alerts.forEach(alert => {
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert';

                const timestamp = new Date(alert.timestamp).toLocaleString();

                alertDiv.innerHTML = `
                    <div>
                        <strong>${alert.alert_type.replace('_', ' ').toUpperCase()}</strong>
                        <span style="margin-left: 10px;">${timestamp}</span>
                        <div style="margin-top: 5px;">${alert.message}</div>
                    </div>
                    <button onclick="acknowledgeAlert(${alert.id})">Dismiss</button>
                `;

                alertsContainer.appendChild(alertDiv);
            });
        })
        .catch(error => console.error('Error loading alerts:', error));
}

// Acknowledge alert
function acknowledgeAlert(alertId) {
    fetch(`/api/alerts/acknowledge/${alertId}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadAlerts();  // Reload alerts
            }
        })
        .catch(error => console.error('Error acknowledging alert:', error));
}

// Load chart data
function loadChart(hours) {
    // Update active button
    document.querySelectorAll('.chart-controls button').forEach(btn => {
        btn.classList.remove('active');
    });

    if (hours === 24) document.getElementById('btn-24h').classList.add('active');
    else if (hours === 168) document.getElementById('btn-7d').classList.add('active');
    else if (hours === 720) document.getElementById('btn-30d').classList.add('active');

    currentTimeframe = hours;

    fetch(`/api/history/${hours}`)
        .then(response => response.json())
        .then(data => {
            drawChart(data);
        })
        .catch(error => console.error('Error loading chart data:', error));
}

// Draw chart
function drawChart(data) {
    const ctx = document.getElementById('chart').getContext('2d');

    // Destroy existing chart if it exists
    if (chart) {
        chart.destroy();
    }

    // Format timestamps
    const labels = data.timestamps.map(ts => {
        const date = new Date(ts);
        if (currentTimeframe <= 24) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else {
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
    });

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Reference Sensor',
                    data: data.reference,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2
                },
                {
                    label: 'Control Sensor',
                    data: data.control,
                    borderColor: '#48c774',
                    backgroundColor: 'rgba(72, 199, 116, 0.1)',
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2
                },
                {
                    label: 'Difference',
                    data: data.difference,
                    borderColor: '#ff6b6b',
                    backgroundColor: 'rgba(255, 107, 107, 0.1)',
                    tension: 0.4,
                    hidden: false,
                    pointRadius: 0,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 10,
                        maxRotation: 45,
                        minRotation: 0
                    }
                }
            }
        }
    });
}

// Calibrate sensor
function calibrate(isEmpty) {
    const sensor = document.getElementById('calibrate-sensor').value;
    const resultDiv = document.getElementById('calibration-result');

    resultDiv.innerHTML = 'Calibrating...';

    fetch('/api/calibrate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            sensor: sensor,
            is_empty: isEmpty
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            resultDiv.innerHTML = `✓ ${sensor} sensor calibrated at ${isEmpty ? 'empty' : 'full'}: Raw value = ${data.raw_value}`;
            resultDiv.style.color = '#48c774';
        } else {
            resultDiv.innerHTML = `✗ Calibration failed: ${data.error || 'Unknown error'}`;
            resultDiv.style.color = '#ff6b6b';
        }

        // Clear message after 5 seconds
        setTimeout(() => {
            resultDiv.innerHTML = '';
        }, 5000);
    })
    .catch(error => {
        resultDiv.innerHTML = `✗ Error: ${error}`;
        resultDiv.style.color = '#ff6b6b';
    });
}

// Tare (zero out) sensor
function tareSensor() {
    const sensor = document.getElementById('calibrate-sensor').value;
    const resultDiv = document.getElementById('calibration-result');

    // Confirmation dialog
    const confirmed = confirm(
        `Are you sure you want to tare the ${sensor} sensor?\n\n` +
        `This will set the current water level as the new 0% baseline. ` +
        `This action cannot be undone without recalibrating.`
    );
    
    if (!confirmed) {
        return;
    }

    resultDiv.innerHTML = 'Taring sensor...';
    resultDiv.style.color = '#82aaff';

    fetch('/api/tare', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            sensor: sensor
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            resultDiv.innerHTML = `✓ ${sensor} sensor tared successfully!<br>` +
                                 `New empty level: ${data.new_empty} (was ${data.old_empty})<br>` +
                                 `Current voltage: ${data.voltage}V`;
            resultDiv.style.color = '#48c774';
            
            // Refresh current readings to show the change
            setTimeout(() => {
                updateCurrent();
            }, 1000);
        } else {
            resultDiv.innerHTML = `✗ Tare failed: ${data.error || 'Unknown error'}`;
            resultDiv.style.color = '#ff6b6b';
        }

        // Clear message after 8 seconds
        setTimeout(() => {
            resultDiv.innerHTML = '';
        }, 8000);
    })
    .catch(error => {
        resultDiv.innerHTML = `✗ Error: ${error}`;
        resultDiv.style.color = '#ff6b6b';
        
        setTimeout(() => {
            resultDiv.innerHTML = '';
        }, 8000);
    });
}
