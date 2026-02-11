#!/usr/bin/env python3
"""
Script to generate views.rst documentation from the view classes.

This script reads the viewlist.py file, extracts _gui_help_txt from each view,
converts markdown to RST, and includes side-by-side screenshots.
"""

import sys
import re
from pathlib import Path


def markdown_to_rst(markdown_text):
    """Convert markdown text to RST format."""
    lines = markdown_text.strip().split('\n')
    rst_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            rst_lines.append('')
            continue
            
        # Convert headers
        if line.startswith('### '):
            title = line[4:]
            rst_lines.append(title)
            rst_lines.append('~' * len(title))
        elif line.startswith('## '):
            title = line[3:]
            rst_lines.append(title)
            rst_lines.append('-' * len(title))
        elif line.startswith('# '):
            title = line[2:]
            rst_lines.append(title)
            rst_lines.append('=' * len(title))
        # Convert bold text (keep RST format)
        elif '**' in line:
            line = re.sub(r'\*\*(.*?)\*\*', r'**\1**', line)
            rst_lines.append(line)
        # Convert bullet points
        elif line.startswith('* '):
            rst_lines.append('- ' + line[2:])
        else:
            rst_lines.append(line)
    
    return '\n'.join(rst_lines)


def check_image_exists(image_path):
    """Check if an image file exists."""
    return Path(image_path).exists()


def generate_views_rst():
    """Generate the views.rst file from view classes."""
    # Get script directory and related paths
    script_dir = Path(__file__).parent.absolute()
    gui_dir = script_dir / "../../spikeinterface_gui"
    output_file = script_dir / "views.rst"

    if output_file.exists():
        print(f"Overwriting existing file: {output_file}")
        output_file.unlink()

    # Add GUI directory to Python path
    sys.path.insert(0, str(gui_dir.absolute()))
    
    # Define view information by parsing files directly (avoiding import issues)
    view_files = {
        'probe': 'probeview.py',
        'unitlist': 'unitlistview.py',
        'spikelist': 'spikelistview.py', 
        'merge': 'mergeview.py',
        'trace': 'traceview.py',
        'waveform': 'waveformview.py',
        'waveformheatmap': 'waveformheatmapview.py',
        'isi': 'isiview.py',
        'correlogram': 'crosscorrelogramview.py',
        'ndscatter': 'ndscatterview.py',
        'similarity': 'similarityview.py',
        'spikeamplitude': 'spikeamplitudeview.py',
        'spikedepth': 'spikedepthview.py',
        'amplitudescalings': 'amplitudescalingsview.py',
        'tracemap': 'tracemapview.py',
        'curation': 'curationview.py',
        'spikerate': 'spikerateview.py',
        'metrics': 'metricsview.py',        
        'mainsettings': 'mainsettingsview.py',
    }
    
    # Extract help text from each view file
    possible_class_views = {}
    
    for view_key, filename in view_files.items():
        view_file_path = gui_dir / filename
        if not view_file_path.exists():
            print(f"Warning: View file not found: {view_file_path}")
            continue
            
        try:
            with open(view_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract _gui_help_txt using regex
            help_match = re.search(r'_gui_help_txt\s*=\s*"""(.*?)"""', content, re.DOTALL)
            if help_match:
                help_text = help_match.group(1).strip()
                # Create a simple class-like object to store the help text
                class ViewInfo:
                    def __init__(self, help_txt):
                        self._gui_help_txt = help_txt
                
                possible_class_views[view_key] = ViewInfo(help_text)
            else:
                print(f"Warning: No _gui_help_txt found in {filename}")
                possible_class_views[view_key] = ViewInfo("No help text available.")
                
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
    
    
    # Start building RST content
    rst_content = '''Views
=====

This page documents all available views in the SpikeInterface GUI, showing their functionality and appearance across different backends (desktop Qt and web panel).

'''
    
    print(f"Processing {len(possible_class_views)} views...")
    
    for view_key, view_class in possible_class_views.items():
        print(f"  Processing view: {view_key}")
        
        # Get the help text
        help_text = getattr(view_class, '_gui_help_txt', 'No help text available.')
        
        # Convert markdown to RST
        rst_help = markdown_to_rst(help_text)
        
        # Define image paths (relative to the RST file)
        desktop_image = f"images/views/desktop/{view_key}.png"
        panel_image = f"images/views/web/{view_key}.png"
        
        # Check if images exist (absolute paths for checking)
        desktop_image_abs = script_dir / desktop_image
        panel_image_abs = script_dir / panel_image
        
        desktop_exists = check_image_exists(desktop_image_abs)
        panel_exists = check_image_exists(panel_image_abs)
        
        if not desktop_exists:
            print(f"    Warning: Desktop image not found: {desktop_image_abs}")
        if not panel_exists:
            print(f"    Warning: Panel image not found: {panel_image_abs}")
        
        # Add view section
        rst_content += f"{rst_help}\n\n"
        
        # Add screenshots section if at least one image exists
        if desktop_exists or panel_exists:
            rst_content += "Screenshots\n"
            rst_content += "~~~~~~~~~~~\n\n"
            
            rst_content += ".. list-table::\n"
            rst_content += "   :widths: 50 50\n"
            rst_content += "   :header-rows: 1\n\n"
            rst_content += "   * - Desktop (Qt)\n"
            rst_content += "     - Web (Panel)\n"
            
            # Desktop image
            if desktop_exists:
                rst_content += f"   * - .. image:: {desktop_image}\n"
                rst_content += "          :width: 100%\n"
            else:
                rst_content += "   * - *Image not available*\n"
            
            # Panel image
            if panel_exists:
                rst_content += f"     - .. image:: {panel_image}\n"
                rst_content += "          :width: 100%\n\n"
            else:
                rst_content += "     - *Image not available*\n\n"
        else:
            print(f"    No images found for view: {view_key}")
            rst_content += "*Screenshots not available for this view.*\n\n"
    
    # Write the RST file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rst_content)
        print(f"\nViews documentation generated successfully at: {output_file}")
        return True
    except Exception as e:
        print(f"Error writing output file: {e}")
        return False


if __name__ == "__main__":
    success = generate_views_rst()
    sys.exit(0 if success else 1)