from flask import Flask, request, render_template, flash, Response, redirect, url_for
import requests
import signal
import threading
from datetime import datetime
import time
import re
import os
from fillpdf import fillpdfs
import sys
import webbrowser
from threading import Timer
from werkzeug.serving import make_server
import socket

#globals
shutdown_event = threading.Event()
_processing_request = False

class ServerThread(threading.Thread):
    def __init__(self, app, port):
        threading.Thread.__init__(self, daemon=True)
        self.port = port
        self.app = app
        self.server = make_server('127.0.0.1', port, app)
        self.ctx = app.app_context()
        self.ctx.push()
        self.is_running = True
        self.error_count = 0

    def run(self):
        try:
            self.server.serve_forever()
        except Exception as e:
            self.error_count += 1
            if self.error_count > 5:
                self.is_running = False
            else:
                try:
                    self.server = make_server('127.0.0.1', self.port, self.app)
                    self.server.serve_forever()
                except Exception:
                    self.is_running = False

    def shutdown(self):
        self.is_running = False
        try:
            self.server.shutdown()
        except Exception:
            pass

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def find_free_port():
    """Find a free port on the system"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def open_browser(port):
    """Open browser after a short delay"""
    webbrowser.open(f'http://127.0.0.1:{port}/')

app = Flask(__name__,
           template_folder=resource_path('templates'),
           static_folder=resource_path('static'))
app.secret_key = 'your_secret_key_here'

def sanitize_filename(filename):
    """Sanitize filename to remove invalid characters."""
    # Replace slashes and other problematic characters with underscores
    invalid_chars = r'[<>:"/\\|?*\']'
    return re.sub(invalid_chars, '_', filename)

def extract_numeric_id(id_str):
    """Extract only numeric characters from an ID string."""
    return ''.join(filter(str.isdigit, str(id_str)))

def standardize_pcp_name(pcp_name):
    """Standardize PCP names to correct format."""
    if pcp_name.lower().strip() in ['de silva', 'dr de silva', 'dr. de silva']:
        return "Janesri De Silva M.D."
    return pcp_name

def normalize_note(note):
    """Normalize a note by removing timestamps, whitespace and common variations."""
    # Remove timestamp pattern
    note = re.sub(r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s*(?:AM|PM)\s*>', '', note)
    # Remove extra whitespace
    note = re.sub(r'\s+', ' ', note)
    # Remove common staff names
    note = re.sub(r'(?:Eresh|Noah|Nisitha|Vihanga|Anchana)(?:\s+\w+)*', '', note)
    return note.strip()

def parse_pcp_note(note_text):
    """Parse PCP change note to extract relevant information."""
    info = {
        'new_pcp': '',
        'eff_date': '',
        'agent_name': '',
        'ref_number': ''
    }
    
    # PCP name mapping
    pcp_mappings = {
        'DE SILVA': "Janesri De Silva M.D.",
        'ARASTU': "Dr. Arastu",
        'JUAREZ MORALES': "Juarez Morales M.D.",
        'JUAREZ': "Juarez Morales M.D.",
        'RODRIGUEZ': "Barbara Rodriguez M.D.",
        'BHATT': "Brian Bhatt M.D.",
        'MINASSIAN': "Guiragos S. Minassian M.D.",
        'BENJAMIN': "Hilma R. Benjamin M.D.",
        'WOODS': "Marianne R. Woods M.D.",
        'SNYDER': "Mark Snyder M.D.",
        'FINEBERG': "Martin Fineberg M.D.",
        'BALA': "Padma Bala M.D.",
        'SHELAT': "Palak Shelat M.D.",
        'KEYNIGSHTEYN': "Rena Keynigshteyn M.D.",
        'MILLET': "Victoria E. Millet M.D.",
        'PARK': "Esther S. Park M.D.",
        'NAT': "Narindar K. Nat M.D.",
        'ZUNIGA': "Jocelyn C. Zuniga M.D.",
        'TAMASHIRO': "Victor G. Tamashiro M.D.",
        'BARBOUR': "Rachel Barbour M.D.",
        'ALTMAN': "Adrienne C. Altman M.D.",
        'UNGS': "Carolina M. Ungs M.D.",
        'BEHROOZAN': "Benjamin Behroozan M.D."
    }
    
    # Find PCP change information with broader pattern matching
    note_text_upper = note_text.upper()
    for pcp_name in pcp_mappings.keys():
        if pcp_name in note_text_upper:
            info['new_pcp'] = pcp_mappings[pcp_name]
            break
    
    # Extract effective date with more patterns
    eff_patterns = [
        r'EFF\s+DATE\s+RETRO\s+(\d{1,2}/\d{1,2}/\d{2,4})',
        r'EFFECTIVE\s+DATE\s+(\d{1,2}/\d{1,2}/\d{2,4})',
        r'EFFECTIVE\s+(\d{1,2}/\d{1,2}/\d{2,4})',
        r'EFF\s+DATE\s+(\d{1,2}/\d{1,2}/\d{2,4})',
        r'EFF\s+(\d{1,2}/?0?\d{1,2}/\d{2,4})',
        r'(\d{1,2}/\d{1,2}/\d{2,4})(?=\s*(?:LINDA|SHEILA|CIANNA|VANESSA|ROXY|MASIMBA|ANDREA|KARINA|$))'
    ]
    
    # First try to find the date in the standard format
    for pattern in eff_patterns:
        eff_match = re.search(pattern, note_text, re.IGNORECASE)
        if eff_match:
            date_str = eff_match.group(1).replace('0/', '/').replace('/0', '/')  # Clean up any bad formatting
            try:
                parsed_date = datetime.strptime(date_str, "%m/%d/%y" if len(date_str.split('/')[-1]) == 2 else "%m/%d/%Y")
                info['eff_date'] = parsed_date.strftime("%m/%d/%Y")
                break
            except ValueError:
                continue
    
    # If no valid date found in the note, try to find it at the end of the input
    if not info['eff_date']:
        # Look for date pattern near the end of the text
        end_date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}\s*[A-Z]+\s*$', note_text)
        if end_date_match:
            date_str = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', end_date_match.group()).group(1)
            try:
                parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
                info['eff_date'] = parsed_date.strftime("%m/%d/%Y")
            except ValueError:
                pass
                
    # Extract reference number - updated pattern
    ref_patterns = [
        r'REF\s*#?\s*([A-Z0-9/-]+)',
        r'REF\.([A-Z0-9/-]+)',
        r'REF\s*\.\s*([A-Z0-9/-]+)',
        r'(?:^|\s)(?:REF|SFA)[-\s]*([A-Z0-9/-]+)',
        r'I-\d+'  # Added pattern for I- references
    ]
    
    for pattern in ref_patterns:
        ref_match = re.search(pattern, note_text)
        if ref_match:
            info['ref_number'] = ref_match.group(1)
            break
    
    # Special case for "Galvez M.A., Nancy"
    if 'GALVEZ' in note_text.upper() and 'NANCY' in note_text.upper():
        info['agent_name'] = "Nancy Galvez"
    else:
        # Extract agent name with more precise pattern
        name_pattern = r'([A-Za-z]+),\s*([A-Za-z]+)(?=\s+\d{2}/\d{2}/\d{4})'
        name_match = re.search(name_pattern, note_text)
        if name_match:
            last_name, first_name = name_match.groups()
            info['agent_name'] = f"{first_name.strip()} {last_name.strip()}"
    
    return info

def extract_patient_data(row):
    """Extract patient data from a single row."""
    columns = row.split('\t')
    if len(columns) < 7:
        return None
        
    try:
        # Clean up the ID field - get only numeric characters
        ktmg_id = extract_numeric_id(columns[1])
        
        # Split the combined fields if they contain '/'
        old_pcp_field = columns[4].split('/')[0].strip() if '/' in columns[4] else columns[4].strip()
        
        patient = {
            'date': columns[0].strip(),
            'ktmg_id': ktmg_id,
            'dob': columns[2].strip(),
            'patient_name': columns[3].split(' DHS ')[0].strip() if ' DHS ' in columns[3] else columns[3].strip(),
            'old_pcp': old_pcp_field,
            'member_id': columns[5].strip(),
            'phone': columns[6].strip()
        }
        
        # Extract member ID if wrapped in asterisks
        member_id_match = re.search(r'\*\*([0-9A-Z]+)\*\*', patient['member_id'])
        if member_id_match:
            patient['member_id'] = member_id_match.group(1)
        
        # Format phone number
        stripped_number = re.sub(r'\D', '', patient['phone'])
        if len(stripped_number) == 10:
            patient['phone'] = f"{stripped_number[:3]}-{stripped_number[3:6]}-{stripped_number[6:]}"
        
        # Format dates
        try:
            patient['date'] = datetime.strptime(patient['date'], "%m/%d/%Y").strftime("%m/%d/%Y")
        except ValueError:
            patient['date'] = ''
            
        try:
            patient['dob'] = datetime.strptime(patient['dob'], "%m/%d/%Y").strftime("%m/%d/%Y")
        except ValueError:
            patient['dob'] = ''
            
        return patient
    except Exception as e:
        print(f"Error processing row: {str(e)}")  # For debugging
        return None

def parse_input(text):
    """Parse the entire input text and match notes with patient data."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    notes = []
    patients = []
    seen_notes = {}  # Use dict to track normalized notes and their original versions
    
    for line in lines:
        # Extended pattern matching for PCP change notes
        note_patterns = [
            'PCP CHANGE TO',
            'PCP WAS MADE TO',
            'PCP WAS CHANGE TO',
            'PCP CHANGE WAS MADE TO',
            'CHANGE TO DR',
            'DR DE SILVA',
            'DR. DE SILVA',
            'DR BEHROOZAN',
            'DR. BEHROOZAN',
            'DR JUAREZ',
            'DR. JUAREZ',
            'TRANSFER WAS MADE',
            'TRANSFER WAS DONE'
        ]
        
        # Check if line contains any note patterns and timestamp
        if (any(pattern in line.upper() for pattern in note_patterns) and 
            ('PM >' in line or 'AM >' in line or 'PM>' in line or 'AM>' in line)):
            # Normalize note for comparison
            normalized_note = normalize_note(line)
            if normalized_note:  # Only process non-empty notes
                if normalized_note not in seen_notes:
                    seen_notes[normalized_note] = line
                    notes.append(line)
        elif '\t' in line and not any(name in line for name in ['Eresh', 'Noah', 'Nisitha', 'Vihanga', 'Anchana']):
            patient = extract_patient_data(line)
            if patient:
                patients.append(patient)
    
    if len(notes) > 0 and len(patients) > 0:
        # Get unique notes in the correct order (using first occurrence)
        unique_notes = list(dict.fromkeys(notes))
        
        # Match notes with patients
        pairs = []
        for i in range(min(len(unique_notes), len(patients))):
            patient = patients[i].copy()
            patient['note'] = unique_notes[i]
            pairs.append(patient)
        
        return pairs
    
    return []

@app.route('/')
def upload_page():
    return render_template('input.html')

@app.before_request
def before_request():
    global _processing_request
    _processing_request = True

@app.after_request
def after_request(response):
    global _processing_request
    _processing_request = False
    return response

@app.route('/process', methods=['POST'])
def process_input():
    try:
        input_text = request.form.get('excel_row', '')
        
        # Basic input validation
        if not input_text or len(input_text.strip()) == 0:
            flash("Error: Empty input received. Please paste valid data.", "error")
            return redirect(url_for('upload_page'))
            
        # First, check if it contains common non-PCP change patterns
        non_pcp_patterns = [
            'LEFT MESSAGE',
            'LEFT MESSAGE/ TEXT',
            'VOICEMAIL',
            'NEED REFERRALS',
            'PT NEED REFERRALS',
            'NEED AUTH',
            'PENDING'
        ]

        if any(pattern in input_text.upper() for pattern in non_pcp_patterns) and not any(phrase in input_text.upper() for phrase in ['PCP CHANGE', 'CHANGE TO DR']):
            flash("This input appears to be a message or referral request, not a PCP change. Please ensure your input includes a PCP change note with doctor name and effective date.", "error")
            return redirect(url_for('upload_page'))
        
        # Parse input and get patient-note pairs
        try:
            patient_pairs = parse_input(input_text)
        except Exception as e:
            flash("Error: Unable to parse input. Please ensure you're pasting the correct format.", "error")
            return redirect(url_for('upload_page'))
        
        if not patient_pairs:
            flash("Error: No valid PCP change found. Input should include a PCP change note with doctor name and effective date, followed by patient information.", "error")
            return redirect(url_for('upload_page'))
        
        processed_files = []
        
        for patient in patient_pairs:
            try:
                # Parse the note associated with this patient
                note_info = parse_pcp_note(patient['note'])
                
                # Check if we have the essential information
                if not note_info['new_pcp'] or not note_info['eff_date']:
                    flash("Error: Could not find required information (new PCP name or effective date) in the note.", "error")
                    return redirect(url_for('upload_page'))
                
                # Combine patient info with note info
                data_dict = {
                    'reqDate': patient['date'],
                    'memberID': patient['member_id'],
                    'ecwID': "New Patient" if not patient['ktmg_id'] else patient['ktmg_id'],
                    'memberName': patient['patient_name'],
                    'mdob': patient['dob'],
                    'phoneNum': patient['phone'],
                    'oldPCP': patient['old_pcp'],
                    'newPCP': note_info['new_pcp'],
                    'effectiveDate': note_info['eff_date'],
                    'agentName': note_info['agent_name'],
                    'fReason': "Patient Requested Change"
                }
                
                # Generate PDF
                pdf_template_path = resource_path('templates/ktmgPcpForm.pdf')
                safe_name = sanitize_filename(patient['patient_name'])
                safe_id = patient['ktmg_id']
                safe_date = patient['date'].replace('/', '-')
                
                output_pdf_name = f"{safe_name}_{safe_id}_PCP-CHANGE-FORM_{safe_date}.pdf"
                output_pdf_path = os.path.expanduser(f"~/Downloads/{output_pdf_name}")
                
                if os.path.exists(output_pdf_path):
                    flash(f"Error: File already exists: {output_pdf_name}. Please try again.", "error")
                    return redirect(url_for('upload_page'))
                
                fillpdfs.write_fillable_pdf(pdf_template_path, output_pdf_path, data_dict, flatten=True)
                processed_files.append(output_pdf_name)
                
            except Exception as e:
                flash(f"Error processing file: {str(e)}", "error")
                return redirect(url_for('upload_page'))
        
        if len(processed_files) == 1:
            return redirect(url_for('confirmation_page', file_name=processed_files[0]))
        else:
            return redirect(url_for('confirmation_page', file_name=f"Generated {len(processed_files)} forms"))
            
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('upload_page'))

@app.route('/confirmation')
def confirmation_page():
    file_name = request.args.get('file_name', '')
    return render_template('confirmation.html', file_name=file_name)

@app.route('/shutdown')
def shutdown():
    global _processing_request, shutdown_event
    
    def delayed_shutdown():
        global _processing_request
        start_time = time.time()
        while _processing_request:
            time.sleep(0.1)
            if time.time() - start_time > 5:  # Timeout after 5 seconds
                break
        shutdown_event.set()
        time.sleep(0.5)
        os._exit(0)
    
    if not getattr(app, 'is_shutting_down', False):
        app.is_shutting_down = True
        threading.Thread(target=delayed_shutdown, daemon=True).start()
    return 'Shutting down...'

@app.route('/health')
def health_check():
    return Response(status=200)

def main():
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            port = find_free_port()
            
            server = ServerThread(app, port)
            server.start()
            Timer(1.5, open_browser, [port]).start()
            
            while server.is_running and not shutdown_event.is_set():
                time.sleep(0.5)
                if not server.is_alive():
                    break
                    
            if shutdown_event.is_set():
                break
                
            retry_count += 1
            time.sleep(1)
            
        except Exception:
            retry_count += 1
            time.sleep(1)
    
    os._exit(0)

if __name__ == '__main__':
    main()