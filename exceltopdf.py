from flask import Flask, request, render_template, send_file, redirect, url_for
from datetime import datetime
from fillpdf import fillpdfs
import re
import os

app = Flask(__name__)

@app.route('/')
def upload_page():
    return render_template('input.html')

@app.route('/process', methods=['POST'])
def process_input():
    # Get the pasted Excel row from the form
    excel_row = request.form['excel_row']
    
    # Default Reason
    reason = "Patient Requested Change"

    # Split the input row using tab as the delimiter
    columns = excel_row.split('\t')

    # Extract necessary data (adjust column indexes based on input)
    date_from_input = columns[0].strip() if len(columns) > 0 else 'N/A'
    dob = columns[2].strip() if len(columns) > 2 else 'N/A'
    patient_name = columns[3].split(' DHS ')[0].strip() if len(columns) > 3 else 'N/A'
    member_id = columns[5].strip() if len(columns) > 5 else 'N/A'
    old_pcp = columns[4].strip() if len(columns) > 4 else 'N/A'

    # Extract patient's phone number (from column after member ID)
    phone_number = columns[6].strip() if len(columns) > 6 else 'N/A'
    stripped_number = re.sub(r'\D', '', phone_number)

    # Check if the stripped number has exactly 10 digits
    if len(stripped_number) == 10:
        # Format the phone number as xxx-xxx-xxxx
        formatted_number = f"{stripped_number[:3]}-{stripped_number[3:6]}-{stripped_number[6:]}"
    else:
        formatted_number = 'N/A'

    # Extract KMTG Member ID (from the second column)
    ktmg_member_id = columns[1].strip() if len(columns) > 1 else 'N/A'

    # Convert date strings to datetime objects and format them
    try:
        date_from_input = datetime.strptime(date_from_input, "%m/%d/%Y").strftime("%m/%d/%Y")
    except ValueError:
        date_from_input = "Invalid Date"

    try:
        dob = datetime.strptime(dob, "%m/%d/%Y").strftime("%m/%d/%Y")
    except ValueError:
        dob = "Invalid Date"

    # Search for "PCP CHANGE" and extract relevant info
    note_section = columns[-1].strip()
    new_pcp = ""
    eff_date = ""
    agent_name = ""

    if "PCP CHANGE" in note_section:
        new_pcp_info = note_section.split("PCP CHANGE TO")[1].split(".")[0].strip()
        new_pcp = new_pcp_info.split("W/")[0].strip()

        # Extract EFF date
        words = new_pcp_info.split()
        for word in words:
            if "/" in word and len(word.split('/')) == 3:  # Likely a date
                try:
                    eff_date = datetime.strptime(word, "%m/%d/%y").strftime("%m/%d/%Y")
                    break
                except ValueError:
                    eff_date = "Invalid Date"

    # Extract agent's name (assuming it is before the timestamp and '>')
    if '>' in note_section:
        agent_info = note_section.split('>')[0].strip()
        agent_name_and_date = agent_info.split('  ')[0].strip()

        parts = agent_name_and_date.rsplit(' ', 2)
        if len(parts) > 1:
            agent_name = f"{parts[-1]} {parts[-2]}"
            agent_name = agent_name.split(',')[0].strip()
        else:
            agent_name = 'N/A'

    # Path to the existing PDF form with a text field
    pdf_template_path = './templates/ktmgPcpForm.pdf'
    output_pdf_name = f"{patient_name}_{ktmg_member_id}_PCP-CHANGE-FORM_{date_from_input.replace('/', '-')}.pdf"
    #output_pdf_path = os.path.expanduser(f"~/Downloads/{output_pdf_name}")
    output_pdf_path = "./finished-pdfs/" + output_pdf_name

    data_dict = {
        'reqDate': date_from_input,
        'memberID': member_id,
        'ecwID': ktmg_member_id,
        'memberName': patient_name,
        'mdob': dob,
        'phoneNum': formatted_number,
        'oldPCP': old_pcp,
        'newPCP': new_pcp,
        'effectiveDate': eff_date,
        'agentName': agent_name,
        'fReason': reason
    }

    fillpdfs.write_fillable_pdf(pdf_template_path, output_pdf_path, data_dict, flatten=True)

    # Render the confirmation template
    return render_template('confirmation.html', file_name=output_pdf_name)

if __name__ == '__main__':
    app.run(debug=True)
