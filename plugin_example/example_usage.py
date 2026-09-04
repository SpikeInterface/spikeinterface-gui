"""
Example usage of the custom view plugin

This script demonstrates how to:
1. Create a simple SortingAnalyzer object
2. Launch the SpikeInterface GUI with the custom view
"""

import spikeinterface.full as si_full
from spikeinterface_gui import run_mainwindow


def create_example_sorting():
    """Create a simple example sorting for demonstration."""
    print("Creating example sorting...")
    
    # Create a simple recording with 4 channels
    recording, sorting = si_full.generate_ground_truth_recording(
        durations=[30.0],  # 30 seconds
        num_channels=4,
        num_units=5,
        sampling_frequency=30000.0,
        seed=0
    )
    
    return recording, sorting


def launch_gui_with_custom_view(recording, sorting):
    """Launch the GUI with a layout that includes the custom view."""
    
    # Create a sorting analyzer (required for the GUI)
    analyzer = si_full.create_sorting_analyzer(
        sorting=sorting,
        recording=recording,
        sparse=False
    )
    
    # Compute waveforms
    analyzer.compute('random_spikes')
    analyzer.compute('noise_levels')
    analyzer.compute('templates')

    # Create a layout that includes the custom view
    # You can combine it with other views
    layout = {
        'zone1': ['unitlist'],  # Our custom view on the left
        'zone2': ['waveform', 'trace'],
        'zone3': ['similarity'],
        'zone4': ['custom1view', 'custom2view'],
    }
    
    # Launch the GUI
    app = run_mainwindow(
        analyzer,
        layout=layout,
        mode="desktop"
    )
    
    return app


def main():
    # Create example data
    recording, sorting = create_example_sorting()
    
    # Launch GUI
    app = launch_gui_with_custom_view(recording, sorting)
    

if __name__ == "__main__":
    main()
