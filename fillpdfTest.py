from fillpdf import fillpdfs

# Path to the existing PDF form with a text field
pdf_template_path = './templates/ktmgPcpForm.pdf'



# Output PDF path
memberName = "john"
ecwID = 1
Date = "1-11-11"


output_pdf_path = str(memberName) + "_" + str(ecwID) + "_" + "PCP-CHANGE-FORM" + "_" + str(Date)  + ".pdf"


fields = fillpdfs.get_form_fields(pdf_template_path)


data_dict = {
    'reqDate': '2024-11-12',
    'memberID': '123456789',
    'ecwID': 'ECW001',
    'memberName': 'John Doe',
    'mdob': '1990-05-15',
    'phoneNum': '555-1234',
    'oldPCP': 'Dr. Smith',
    'newPCP': 'Dr. Johnson',
    'effectiveDate': '2024-12-01',
    'agentName': 'Alice Williams',
    'fReason': 'Relocation'
}


fillpdfs.write_fillable_pdf(pdf_template_path, output_pdf_path, data_dict)

fillpdfs.write_fillable_pdf(pdf_template_path, output_pdf_path, data_dict, flatten=True)

fillpdfs.print_form_fields(output_pdf_path)


# Fill the form
#fillpdfs.place_text('Yooooooo', 300, 500, pdf_template_path, output_pdf_path, 1)


print(f"Form filled successfully! Output saved to {output_pdf_path}")



#print("\nYo here is the first form: f1: " + str(fields.get('memberID')))
#print("\nYo here is the 2nd form: f2: " + str(fields.get('ecwID')))

#filling in the boxes:



#fillpdfs.write_fillable_pdf(pdf_template_path, output_pdf_path, data_dict)


""" f"Date: {date_from_input}\n"
        f"Patient Name: {patient_name}\n"
        f"Date of Birth: {dob}\n"
        f"Member ID: {member_id}\n"
        f"KTMG Member ID: {ktmg_member_id}\n"
        f"Phone Number: {formatted_number}\n"
        f"Old PCP: {old_pcp}\n"
        f"New PCP: {new_pcp}\n"
        f"Effective Date: {eff_date}\n"
        f"Agent Name: {agent_name}\n"
        f"Reason For Change: {reason}\n" """    