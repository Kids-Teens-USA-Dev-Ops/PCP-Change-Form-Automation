import PyInstaller.__main__
import os
import shutil

def create_executable():
    # Create temporary directories if they don't exist
    os.makedirs('dist/templates', exist_ok=True)
    os.makedirs('dist/static', exist_ok=True)
    
    # Copy template and static files
    shutil.copy('templates/input.html', 'dist/templates/')
    shutil.copy('templates/confirmation.html', 'dist/templates/')
    shutil.copy('templates/ktmgPcpForm.pdf', 'dist/templates/')
    shutil.copy('static/logos.png', 'dist/static/')
    
    # Define PyInstaller arguments
    pyi_args = [
        'exceltopdf2.py',  # Your main script
        '--onefile',  # Create a single executable
        '--add-data', f'templates{os.pathsep}templates',  # Include templates directory
        '--add-data', f'static{os.pathsep}static',  # Include static directory
        '--hidden-import', 'fillpdf',
        '--hidden-import', 'webbrowser',
        '--hidden-import', 'socket',
        '--hidden-import', 'engineio.async_drivers.threading',
        '--name', 'Auto PCP Change Form',
        '--icon', 'icon.ico',  # Updated to use your icon file
        '--noconsole',
        '--clean'
    ]
    
    # Run PyInstaller
    PyInstaller.__main__.run(pyi_args)

if __name__ == '__main__':
    create_executable()