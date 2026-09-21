# MavsAI_Employee_Birthday_and_Anniversary_Celebrations
These are all the codes I created to successfully complete another one of my Mavs AI Internship projects. Details of each program included below.

The CloudFormation Template deploys the entire required AWS infrastructure within seconds. It creates the following components with their respective use-cases:
  1. AWS Lambda --> Runs the Python file to execute the actual command
  2. Amazon EventBridge --> Sets-up a CRON job schedule to invoke the Lambda function every day at 09:00 IST.
  3. Simple Email Service (SES) --> Sends an email to everybody at Mavs AI announcing the occasion in case of one.

The HTML code creates how the email should look like when received by the employees at Mavs AI. It designs the text, background, emojis, colors, and more.

The Python code is the heart of it all. It is the code that goes and checks an Excel Online file that stores all company data for employees' birthdays and work anniversaries. It then verifies if somebody has their special occasion on that particular date or not. If they do not, it does not do anything further. If they do, it sends the rendered email to every employee via SES.
