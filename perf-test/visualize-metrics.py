#!/usr/bin/env python3
"""
Resource Metrics Visualization Tool

Generates charts from resource-metrics.csv files created during performance tests.

Usage:
    python3 visualize-metrics.py <metrics_csv_file> [output_dir]

Example:
    python3 visualize-metrics.py ./results/perf-results-20251109/small/resource-metrics.csv ./results/perf-results-20251109/small/

Output:
    - cpu_usage.png: CPU usage over time
    - memory_usage.png: Memory usage over time
    - combined_metrics.png: Combined view of all metrics
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

def load_metrics(csv_file):
    """Load metrics from CSV file"""
    try:
        df = pd.read_csv(csv_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        print(f"Error loading metrics: {e}")
        sys.exit(1)

def plot_cpu_usage(df, output_file):
    """Plot CPU usage over time"""
    fig, ax = plt.subplots(figsize=(14, 6))

    containers = df['container'].unique()
    colors = {'fluxgate-perf-edge': '#2E86AB',
              'fluxgate-perf-backend': '#A23B72',
              'fluxgate-perf-postgres': '#F18F01'}

    for container in containers:
        container_df = df[df['container'] == container]
        color = colors.get(container, '#333333')
        ax.plot(container_df['timestamp'], container_df['cpu_percent'],
                label=container.replace('fluxgate-perf-', '').title(),
                linewidth=2, color=color, alpha=0.8)

    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('CPU Usage (%)', fontsize=12)
    ax.set_title('CPU Usage Over Time', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"✓ Created: {output_file}")

def plot_memory_usage(df, output_file):
    """Plot memory usage over time"""
    fig, ax = plt.subplots(figsize=(14, 6))

    containers = df['container'].unique()
    colors = {'fluxgate-perf-edge': '#2E86AB',
              'fluxgate-perf-backend': '#A23B72',
              'fluxgate-perf-postgres': '#F18F01'}

    for container in containers:
        container_df = df[df['container'] == container]
        color = colors.get(container, '#333333')
        ax.plot(container_df['timestamp'], container_df['memory_usage_mb'],
                label=container.replace('fluxgate-perf-', '').title(),
                linewidth=2, color=color, alpha=0.8)

    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Memory Usage (MB)', fontsize=12)
    ax.set_title('Memory Usage Over Time', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"✓ Created: {output_file}")

def plot_memory_percent(df, output_file):
    """Plot memory percentage over time"""
    fig, ax = plt.subplots(figsize=(14, 6))

    containers = df['container'].unique()
    colors = {'fluxgate-perf-edge': '#2E86AB',
              'fluxgate-perf-backend': '#A23B72',
              'fluxgate-perf-postgres': '#F18F01'}

    for container in containers:
        container_df = df[df['container'] == container]
        color = colors.get(container, '#333333')
        ax.plot(container_df['timestamp'], container_df['memory_percent'],
                label=container.replace('fluxgate-perf-', '').title(),
                linewidth=2, color=color, alpha=0.8)

    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Memory Usage (% of Limit)', fontsize=12)
    ax.set_title('Memory Usage (%) Over Time', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"✓ Created: {output_file}")

def plot_combined_metrics(df, output_file):
    """Plot combined CPU and memory metrics"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    containers = df['container'].unique()
    colors = {'fluxgate-perf-edge': '#2E86AB',
              'fluxgate-perf-backend': '#A23B72',
              'fluxgate-perf-postgres': '#F18F01'}

    # CPU usage
    for container in containers:
        container_df = df[df['container'] == container]
        color = colors.get(container, '#333333')
        ax1.plot(container_df['timestamp'], container_df['cpu_percent'],
                label=container.replace('fluxgate-perf-', '').title(),
                linewidth=2, color=color, alpha=0.8)

    ax1.set_ylabel('CPU Usage (%)', fontsize=12)
    ax1.set_title('CPU and Memory Usage Over Time', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Memory usage
    for container in containers:
        container_df = df[df['container'] == container]
        color = colors.get(container, '#333333')
        ax2.plot(container_df['timestamp'], container_df['memory_usage_mb'],
                label=container.replace('fluxgate-perf-', '').title(),
                linewidth=2, color=color, alpha=0.8)

    ax2.set_xlabel('Time', fontsize=12)
    ax2.set_ylabel('Memory Usage (MB)', fontsize=12)
    ax2.legend(loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"✓ Created: {output_file}")

def plot_network_io(df, output_file):
    """Plot network I/O over time"""
    fig, ax = plt.subplots(figsize=(14, 6))

    containers = df['container'].unique()
    colors = {'fluxgate-perf-edge': '#2E86AB',
              'fluxgate-perf-backend': '#A23B72',
              'fluxgate-perf-postgres': '#F18F01'}

    for container in containers:
        container_df = df[df['container'] == container]
        color = colors.get(container, '#333333')

        # Plot RX (received)
        ax.plot(container_df['timestamp'], container_df['net_io_rx_mb'],
                label=f"{container.replace('fluxgate-perf-', '').title()} RX",
                linewidth=2, color=color, alpha=0.8, linestyle='-')

        # Plot TX (transmitted)
        ax.plot(container_df['timestamp'], container_df['net_io_tx_mb'],
                label=f"{container.replace('fluxgate-perf-', '').title()} TX",
                linewidth=2, color=color, alpha=0.5, linestyle='--')

    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Network I/O (MB)', fontsize=12)
    ax.set_title('Network I/O Over Time', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"✓ Created: {output_file}")

def generate_summary_stats(df, output_file):
    """Generate summary statistics"""
    with open(output_file, 'w') as f:
        f.write("# Resource Usage Summary Statistics\n\n")

        for container in df['container'].unique():
            container_df = df[df['container'] == container]

            f.write(f"## {container}\n\n")

            # CPU stats
            f.write("### CPU Usage\n")
            f.write(f"- Average: {container_df['cpu_percent'].mean():.2f}%\n")
            f.write(f"- Min: {container_df['cpu_percent'].min():.2f}%\n")
            f.write(f"- Max: {container_df['cpu_percent'].max():.2f}%\n")
            f.write(f"- Std Dev: {container_df['cpu_percent'].std():.2f}%\n")
            f.write(f"- P50 (Median): {container_df['cpu_percent'].quantile(0.5):.2f}%\n")
            f.write(f"- P95: {container_df['cpu_percent'].quantile(0.95):.2f}%\n")
            f.write(f"- P99: {container_df['cpu_percent'].quantile(0.99):.2f}%\n\n")

            # Memory stats
            f.write("### Memory Usage\n")
            f.write(f"- Average: {container_df['memory_usage_mb'].mean():.2f} MB\n")
            f.write(f"- Min: {container_df['memory_usage_mb'].min():.2f} MB\n")
            f.write(f"- Max: {container_df['memory_usage_mb'].max():.2f} MB\n")
            f.write(f"- Std Dev: {container_df['memory_usage_mb'].std():.2f} MB\n")
            f.write(f"- Average %: {container_df['memory_percent'].mean():.2f}%\n")
            f.write(f"- Max %: {container_df['memory_percent'].max():.2f}%\n\n")

            # Network I/O
            f.write("### Network I/O\n")
            f.write(f"- Total RX: {container_df['net_io_rx_mb'].iloc[-1]:.2f} MB\n")
            f.write(f"- Total TX: {container_df['net_io_tx_mb'].iloc[-1]:.2f} MB\n\n")

            f.write("---\n\n")

    print(f"✓ Created: {output_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 visualize-metrics.py <metrics_csv_file> [output_dir]")
        sys.exit(1)

    metrics_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(metrics_file)

    if not os.path.exists(metrics_file):
        print(f"Error: Metrics file not found: {metrics_file}")
        sys.exit(1)

    print(f"Loading metrics from: {metrics_file}")
    df = load_metrics(metrics_file)

    print(f"Loaded {len(df)} data points for {len(df['container'].unique())} containers")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate plots
    print("Generating visualizations...")
    plot_cpu_usage(df, os.path.join(output_dir, 'cpu_usage.png'))
    plot_memory_usage(df, os.path.join(output_dir, 'memory_usage_mb.png'))
    plot_memory_percent(df, os.path.join(output_dir, 'memory_usage_percent.png'))
    plot_combined_metrics(df, os.path.join(output_dir, 'combined_metrics.png'))
    plot_network_io(df, os.path.join(output_dir, 'network_io.png'))

    # Generate summary stats
    print()
    print("Generating summary statistics...")
    generate_summary_stats(df, os.path.join(output_dir, 'resource-summary.md'))

    print()
    print("✓ All visualizations created successfully!")
    print(f"Output directory: {output_dir}")

if __name__ == '__main__':
    main()
