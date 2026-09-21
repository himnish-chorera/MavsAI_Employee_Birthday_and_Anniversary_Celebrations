import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
import os
import boto3

# Environment variables
TENANT_ID = os.environ['TENANT_ID']
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
DRIVE_ID = os.environ['DRIVE_ID']
ITEM_ID = os.environ['ITEM_ID']
SHEET_NAME = os.environ['SHEET_NAME']
SENDER_EMAIL = os.environ['SENDER_EMAIL']
RECIPIENT_EMAIL = os.environ['RECIPIENT_EMAIL']

# Fetch AWS Region automatically provided by Lambda runtime
AWS_REGION = os.environ['AWS_REGION']

def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default',
        'grant_type': 'client_credentials'
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())['access_token']

def lambda_handler(event, context):
    try:
        # 1. Authenticate with Microsoft Graph
        token = get_access_token()
        
        # 2. Fetch Excel Data
        encoded_sheet_name = urllib.parse.quote(SHEET_NAME)
        graph_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{ITEM_ID}/workbook/worksheets('{encoded_sheet_name}')/usedRange"
        
        req = urllib.request.Request(graph_url)
        req.add_header('Authorization', f'Bearer {token}')
        
        with urllib.request.urlopen(req) as response:
            excel_data = json.loads(response.read())
            
        grid = excel_data.get('text', []) 
        if len(grid) < 2:
            return {"statusCode": 200, "body": "No data found."}
            
        headers = [str(h).strip() for h in grid[0]]
        rows = grid[1:]
        
        try:
            name_idx = headers.index('Name')
            dob_idx = headers.index('DOB')
            join_idx = headers.index('Joining Date')
        except ValueError:
            return {"statusCode": 500, "body": "Missing required columns."}
            
        # 3. Match Dates (IST Offset)
        ist_offset = timedelta(hours=5, minutes=30)
        today = datetime.now(timezone.utc) + ist_offset
        current_day_month = today.strftime("%d-%b").lower()
        current_year = today.year
        
        birthdays = []
        anniversaries = []
        
        for row in rows:
            if len(row) <= max(name_idx, dob_idx, join_idx): continue
            
            name = str(row[name_idx]).strip()
            # Handle DD/MMM/YYYY or DD-MMM-YYYY by normalizing to -
            dob = str(row[dob_idx]).strip().replace('/', '-').replace(' ', '-').lower()
            joining = str(row[join_idx]).strip().replace('/', '-').replace(' ', '-').lower()
            
            if len(dob) >= 6 and dob[:6] == current_day_month:
                birthdays.append(name)
                
            if len(joining) >= 6 and joining[:6] == current_day_month:
                join_year = joining[-4:]
                if join_year.isdigit():
                    years = current_year - int(join_year)
                    if years > 0:
                        anniversaries.append((name, years))
                        
        # 4. Construct HTML Email Message
        if not birthdays and not anniversaries:
            return {"statusCode": 200, "body": "No events today."}
            
        # Generate the dynamic content section
        dynamic_content = ""
        
        if birthdays:
            dynamic_content += '<div class="section-title title-bday">🎂 Birthdays</div>'
            for b in birthdays:
                dynamic_content += f'''
                <table width="100%" cellpadding="0" cellspacing="0"><tr><td class="item-row"><table width="100%" cellpadding="0" cellspacing="0">
                    <tr><td width="60" valign="middle"><div class="icon-box bg-light">🥳</div></td>
                    <td valign="middle" class="text-wrap">
                        <div class="name">{b}</div><div class="sub">Have an absolutely fantastic day!</div><div class="pill pill-light">Birthday today</div>
                    </td></tr></table></td></tr></table>'''
                    
        if birthdays and anniversaries:
            dynamic_content += '<div class="divider"></div>'
            
        if anniversaries:
            dynamic_content += '<div class="section-title title-anni">💼 Anniversaries</div>'
            for name, years in anniversaries:
                dynamic_content += f'''
                <table width="100%" cellpadding="0" cellspacing="0"><tr><td class="item-row-dark"><table width="100%" cellpadding="0" cellspacing="0">
                    <tr><td width="60" valign="middle"><div class="icon-box bg-dark-icon">⭐</div></td>
                    <td valign="middle" class="text-wrap">
                        <div class="name-dark">{name}</div><div class="sub-dark">Thank you for your dedication.</div><div class="pill pill-yellow">{years} Years Milestone</div>
                    </td></tr></table></td></tr></table>'''

        # Read the HTML template file and insert the dynamic content
        with open('email_template.html', 'r', encoding='utf-8') as f:
            template_html = f.read()
        
        final_html = template_html.replace('{{DYNAMIC_CONTENT}}', dynamic_content)
        
        # 5. Send via Amazon SES
        ses_client = boto3.client('ses', region_name=AWS_REGION)
        ses_client.send_email(
            Source=SENDER_EMAIL,
            Destination={'ToAddresses': [RECIPIENT_EMAIL]},
            Message={
                'Subject': {'Data': "Today's Company Birthdays & Anniversaries!"},
                'Body': {'Html': {'Data': final_html}}
            }
        )
        
        return {"statusCode": 200, "body": "Email sent successfully!"}
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": str(e)}