from flask import Flask, request, render_template
from datetime import datetime
from fillpdf import fillpdfs
import re

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
    
    # Extract KMTG Member ID (from second column)
    ktmg_member_id = columns[1].strip() if len(columns) > 1 else 'N/A'

    # Convert date strings to datetime objects and format them
    try:
        date_from_input = datetime.strptime(date_from_input, "%m/%d/%Y").strftime("%B %d, %Y")
    except ValueError:
        date_from_input = "Invalid Date"

    try:
        dob = datetime.strptime(dob, "%m/%d/%Y").strftime("%B %d, %Y")
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
                    eff_date = datetime.strptime(word, "%m/%d/%y").strftime("%B %d, %Y")
                    break
                except ValueError:
                    eff_date = "Invalid Date"

    # Extract agent's name (assuming it is before the timestamp and '>')
    if '>' in note_section:
        # Split the note section at '>' and get the part before it
        agent_info = note_section.split('>')[0].strip()
    
        # Find the first occurrence of a space before the comma and cut all text before the name
        agent_name_and_date = agent_info.split('  ')[0].strip()  # We expect double spaces between name and timestamp

        parts = agent_name_and_date.rsplit(' ', 2)  # Split from the right by 2 spaces
        if len(parts) > 1:
            agent_name = f"{parts[-1]} {parts[-2]}"  # Assign First Last name
            agent_name = agent_name.split(',')[0].strip()
        else:
            agent_name = 'N/A'

    # Debug output for verification
    debug_output = (
        f"Date: {date_from_input}\n"
        f"Patient Name: {patient_name}\n"
        f"Date of Birth: {dob}\n"
        f"Member ID: {member_id}\n"
        f"KTMG Member ID: {ktmg_member_id}\n"
        f"Phone Number: {formatted_number}\n"
        f"Old PCP: {old_pcp}\n"
        f"New PCP: {new_pcp}\n"
        f"Effective Date: {eff_date}\n"
        f"Agent Name: {agent_name}\n"
        f"Reason For Change: {reason}\n"
    )

    
    # Path to the existing PDF form with a text field
    pdf_template_path = './templates/ktmgPcpForm.pdf'

    output_pdf_path = str(patient_name) + "_" + str(ktmg_member_id) + "_" + "PCP-CHANGE-FORM" + "_" + str(date_from_input)  + ".pdf"


    data_dict = {
        'reqDate': f"{date_from_input}",
        'memberID': f"{member_id}",
        'ecwID': f"{ktmg_member_id}",
        'memberName': f"{patient_name}",
        'mdob': f"{dob}",
        'phoneNum': f"{formatted_number}",
        'oldPCP': f"{old_pcp}",
        'newPCP': f"{new_pcp}",
        'effectiveDate': f"{eff_date}",
        'agentName': f"{agent_name}",
        'fReason': f"{reason}"
    }

    fillpdfs.write_fillable_pdf(pdf_template_path, output_pdf_path, data_dict, flatten=True)

    fillpdfs.print_form_fields(output_pdf_path)
    
    
    # Return debug output as plain text
    return f"<pre>{debug_output}</pre>"

if __name__ == '__main__':
    app.run(debug=True)
