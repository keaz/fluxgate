#!/usr/bin/env python3
"""
Performance Test Chart Generator
Generates comprehensive charts from k6 performance test results
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
import sys
import os
from pathlib import Path

def load_summary_data(json_file):
    """Load k6 summary JSON file"""
    with open(json_file, 'r') as f:
        return json.load(f)

def extract_metrics(data):
    """Extract key metrics from k6 summary data"""
    metrics = data.get('metrics', {})

    # HTTP request duration metrics
    http_duration = metrics.get('http_req_duration', {}).get('values', {})

    # Iteration metrics
    iteration_duration = metrics.get('iteration_duration', {}).get('values', {})

    # Request counts
    http_reqs = metrics.get('http_reqs', {}).get('values', {})

    # Error rates
    http_failed = metrics.get('http_req_failed', {}).get('values', {})
    eval_errors = metrics.get('evaluation_errors', {}).get('values', {})

    # Checks
    checks = metrics.get('checks', {}).get('values', {})

    # VUs
    vus = metrics.get('vus_max', {}).get('values', {})

    # Data transfer
    data_sent = metrics.get('data_sent', {}).get('values', {})
    data_received = metrics.get('data_received', {}).get('values', {})

    # Test duration
    test_duration = data.get('state', {}).get('testRunDurationMs', 0) / 1000  # Convert to seconds

    return {
        'http_duration': http_duration,
        'iteration_duration': iteration_duration,
        'http_reqs': http_reqs,
        'http_failed': http_failed,
        'eval_errors': eval_errors,
        'checks': checks,
        'vus': vus,
        'data_sent': data_sent,
        'data_received': data_received,
        'test_duration': test_duration
    }

def create_latency_chart(ax, metrics, title):
    """Create latency percentile chart"""
    http_duration = metrics['http_duration']

    percentiles = ['min', 'med', 'avg', 'p(90)', 'p(95)', 'max']
    values = [http_duration.get(p, 0) for p in percentiles]

    colors = ['#2ecc71', '#3498db', '#9b59b6', '#f39c12', '#e67e22', '#e74c3c']
    bars = ax.bar(percentiles, values, color=colors, edgecolor='black', linewidth=1.2)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}ms',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylabel('Latency (ms)', fontsize=11, fontweight='bold')
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Add threshold line at 500ms
    ax.axhline(y=500, color='red', linestyle='--', linewidth=2, alpha=0.7, label='P95 Threshold (500ms)')
    ax.legend(loc='upper left', fontsize=9)

def create_throughput_chart(ax, metrics):
    """Create throughput chart"""
    http_reqs = metrics['http_reqs']
    test_duration = metrics['test_duration']

    total_requests = http_reqs.get('count', 0)
    rps = http_reqs.get('rate', 0)

    categories = ['Total Requests', 'Requests/sec', 'Test Duration (s)']
    values = [total_requests, rps, test_duration]
    colors = ['#3498db', '#2ecc71', '#9b59b6']

    # Normalize for visualization (different scales)
    normalized_values = [
        total_requests / 1000,  # Show in thousands
        rps,
        test_duration / 10  # Scale down for visibility
    ]

    bars = ax.bar(categories, normalized_values, color=colors, edgecolor='black', linewidth=1.2)

    # Add actual value labels
    labels = [f'{total_requests:,}', f'{rps:.2f}', f'{test_duration:.1f}s']
    for bar, label in zip(bars, labels):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                label,
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylabel('Value (normalized)', fontsize=11, fontweight='bold')
    ax.set_title('Throughput Metrics', fontsize=12, fontweight='bold', pad=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha='right')

def create_error_rate_chart(ax, metrics):
    """Create error rate and success rate chart"""
    checks = metrics['checks']
    http_failed = metrics['http_failed']
    eval_errors = metrics['eval_errors']

    # Success rate
    success_rate = checks.get('rate', 0) * 100
    failure_rate = 100 - success_rate

    # HTTP failure rate
    http_fail_rate = http_failed.get('rate', 0) * 100
    http_success_rate = 100 - http_fail_rate

    # Evaluation error rate
    eval_error_rate = eval_errors.get('rate', 0) * 100
    eval_success_rate = 100 - eval_error_rate

    categories = ['Checks', 'HTTP Requests', 'Evaluations']
    success_rates = [success_rate, http_success_rate, eval_success_rate]
    failure_rates = [failure_rate, http_fail_rate, eval_error_rate]

    x = np.arange(len(categories))
    width = 0.6

    bars1 = ax.bar(x, success_rates, width, label='Success', color='#2ecc71', edgecolor='black', linewidth=1.2)
    bars2 = ax.bar(x, failure_rates, width, bottom=success_rates, label='Failure', color='#e74c3c', edgecolor='black', linewidth=1.2)

    # Add percentage labels
    for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
        # Success label
        if success_rates[i] > 5:
            ax.text(bar1.get_x() + bar1.get_width()/2., success_rates[i]/2,
                    f'{success_rates[i]:.2f}%',
                    ha='center', va='center', fontsize=9, fontweight='bold', color='white')

        # Failure label
        if failure_rates[i] > 0.1:
            ax.text(bar2.get_x() + bar2.get_width()/2., success_rates[i] + failure_rates[i]/2,
                    f'{failure_rates[i]:.3f}%',
                    ha='center', va='center', fontsize=8, fontweight='bold', color='white')

    ax.set_ylabel('Percentage (%)', fontsize=11, fontweight='bold')
    ax.set_title('Success vs Error Rates', fontsize=12, fontweight='bold', pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend(loc='lower right', fontsize=10)
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

def create_data_transfer_chart(ax, metrics):
    """Create data transfer chart"""
    data_sent = metrics['data_sent'].get('count', 0) / (1024 * 1024)  # Convert to MB
    data_received = metrics['data_received'].get('count', 0) / (1024 * 1024)  # Convert to MB

    categories = ['Data Sent', 'Data Received']
    values = [data_sent, data_received]
    colors = ['#3498db', '#2ecc71']

    bars = ax.bar(categories, values, color=colors, edgecolor='black', linewidth=1.2)

    # Add value labels
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f} MB',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylabel('Data Transfer (MB)', fontsize=11, fontweight='bold')
    ax.set_title('Network Data Transfer', fontsize=12, fontweight='bold', pad=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

def create_test_summary_table(ax, metrics, config):
    """Create test summary table"""
    ax.axis('off')

    # Extract configuration
    total_features = config.get('totalFeatures', 'N/A')
    target_rps = config.get('targetRPS', 'N/A')
    steady_duration = config.get('steadyDuration', 'N/A')
    p95_threshold = config.get('p95Latency', 'N/A')
    p99_threshold = config.get('p99Latency', 'N/A')
    error_rate_threshold = config.get('errorRate', 'N/A')

    # Extract results
    http_duration = metrics['http_duration']
    http_reqs = metrics['http_reqs']
    checks = metrics['checks']
    vus_max = metrics['vus'].get('max', 'N/A')

    # Determine pass/fail
    p95_pass = http_duration.get('p(95)', 0) < p95_threshold if p95_threshold != 'N/A' else True
    error_pass = checks.get('rate', 0) >= (1 - error_rate_threshold) if error_rate_threshold != 'N/A' else True

    # Create table data
    table_data = [
        ['Metric', 'Value', 'Status'],
        ['Total Features', f'{total_features:,}', ''],
        ['Target RPS', str(target_rps), ''],
        ['Max VUs', str(vus_max), ''],
        ['Actual RPS', f"{http_reqs.get('rate', 0):.2f}", ''],
        ['Total Requests', f"{http_reqs.get('count', 0):,}", ''],
        ['Test Duration', f"{metrics['test_duration']:.1f}s", ''],
        ['P50 Latency', f"{http_duration.get('med', 0):.2f}ms", ''],
        ['P95 Latency', f"{http_duration.get('p(95)', 0):.2f}ms", '✓ PASS' if p95_pass else '✗ FAIL'],
        ['Success Rate', f"{checks.get('rate', 0) * 100:.3f}%", '✓ PASS' if error_pass else '✗ FAIL'],
    ]

    # Color coding
    colors = [['#34495e', '#34495e', '#34495e']]  # Header
    for i in range(1, len(table_data)):
        if 'PASS' in table_data[i][2]:
            row_color = ['#ecf0f1', '#ecf0f1', '#d5f4e6']
        elif 'FAIL' in table_data[i][2]:
            row_color = ['#ecf0f1', '#ecf0f1', '#f8d7da']
        else:
            row_color = ['#ecf0f1', '#ecf0f1', '#ecf0f1']
        colors.append(row_color)

    table = ax.table(cellText=table_data, cellLoc='left', loc='center',
                     cellColours=colors, colWidths=[0.4, 0.3, 0.3])

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # Style header row
    for i in range(3):
        cell = table[(0, i)]
        cell.set_text_props(weight='bold', color='white')
        cell.set_facecolor('#34495e')

    # Style data rows
    for i in range(1, len(table_data)):
        for j in range(3):
            cell = table[(i, j)]
            if j == 2 and ('PASS' in table_data[i][2] or 'FAIL' in table_data[i][2]):
                cell.set_text_props(weight='bold')

    ax.set_title('Test Summary', fontsize=12, fontweight='bold', pad=20)

def create_latency_breakdown_chart(ax, metrics):
    """Create HTTP request timing breakdown chart"""
    http_metrics = metrics

    # Extract timing components (in ms)
    blocked = http_metrics.get('http_req_blocked', {}).get('values', {}).get('avg', 0)
    connecting = http_metrics.get('http_req_connecting', {}).get('values', {}).get('avg', 0)
    tls = http_metrics.get('http_req_tls_handshaking', {}).get('values', {}).get('avg', 0)
    sending = http_metrics.get('http_req_sending', {}).get('values', {}).get('avg', 0)
    waiting = http_metrics.get('http_req_waiting', {}).get('values', {}).get('avg', 0)
    receiving = http_metrics.get('http_req_receiving', {}).get('values', {}).get('avg', 0)

    data = metrics['metrics']
    blocked = data.get('http_req_blocked', {}).get('values', {}).get('avg', 0)
    connecting = data.get('http_req_connecting', {}).get('values', {}).get('avg', 0)
    tls = data.get('http_req_tls_handshaking', {}).get('values', {}).get('avg', 0)
    sending = data.get('http_req_sending', {}).get('values', {}).get('avg', 0)
    waiting = data.get('http_req_waiting', {}).get('values', {}).get('avg', 0)
    receiving = data.get('http_req_receiving', {}).get('values', {}).get('avg', 0)

    labels = ['Blocked', 'Connecting', 'TLS', 'Sending', 'Waiting', 'Receiving']
    values = [blocked, connecting, tls, sending, waiting, receiving]
    colors = ['#e74c3c', '#e67e22', '#f39c12', '#f1c40f', '#2ecc71', '#3498db']

    # Create horizontal bar chart
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=colors, edgecolor='black', linewidth=1.2)

    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, values)):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2.,
                f' {val:.3f}ms',
                ha='left', va='center', fontsize=9, fontweight='bold')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel('Time (ms)', fontsize=11, fontweight='bold')
    ax.set_title('HTTP Request Timing Breakdown (Avg)', fontsize=12, fontweight='bold', pad=10)
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

def generate_performance_report(summary_file, output_file=None):
    """Generate comprehensive performance report"""
    # Load data
    data = load_summary_data(summary_file)
    metrics_raw = extract_metrics(data)
    metrics_raw['metrics'] = data.get('metrics', {})

    config = data.get('setup_data', {}).get('config', {})

    # Create figure with subplots
    fig = plt.figure(figsize=(20, 12))
    fig.suptitle('FluxGate Edge Server Performance Test Report',
                 fontsize=16, fontweight='bold', y=0.98)

    # Create grid layout
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3,
                  left=0.06, right=0.97, top=0.94, bottom=0.05)

    # Create subplots
    ax1 = fig.add_subplot(gs[0, 0:2])  # Latency chart (wider)
    ax2 = fig.add_subplot(gs[0, 2])    # Throughput chart
    ax3 = fig.add_subplot(gs[1, 0])    # Error rate chart
    ax4 = fig.add_subplot(gs[1, 1])    # Data transfer chart
    ax5 = fig.add_subplot(gs[1, 2])    # Latency breakdown
    ax6 = fig.add_subplot(gs[2, :])    # Summary table (full width)

    # Generate charts
    create_latency_chart(ax1, metrics_raw, 'HTTP Request Duration (Latency Percentiles)')
    create_throughput_chart(ax2, metrics_raw)
    create_error_rate_chart(ax3, metrics_raw)
    create_data_transfer_chart(ax4, metrics_raw)
    create_latency_breakdown_chart(ax5, metrics_raw)
    create_test_summary_table(ax6, metrics_raw, config)

    # Add footer with test info
    test_name = Path(summary_file).stem
    fig.text(0.5, 0.01, f'Test: {test_name} | Generated: {os.popen("date").read().strip()}',
             ha='center', fontsize=9, style='italic', color='gray')

    # Save or show
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Performance report saved to: {output_file}")
    else:
        plt.show()

    plt.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_perf_charts.py <summary-json-file> [output-png-file]")
        print("\nExample:")
        print("  python generate_perf_charts.py results/perf-results-20251112-055815/tiny/steady-100-summary.json")
        print("  python generate_perf_charts.py results/perf-results-20251112-055815/tiny/steady-100-summary.json report.png")
        sys.exit(1)

    summary_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(summary_file):
        print(f"Error: File not found: {summary_file}")
        sys.exit(1)

    # If output file not specified, auto-generate name
    if not output_file:
        base_path = Path(summary_file).parent
        test_name = Path(summary_file).stem
        output_file = base_path / f"{test_name}-report.png"

    generate_performance_report(summary_file, str(output_file))

if __name__ == '__main__':
    main()
