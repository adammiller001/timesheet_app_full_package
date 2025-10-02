# Google Sheets Setup Guide

This guide will help you set up Google Sheets integration for your PTW Timesheet App, eliminating the need for manual Excel file syncing.

## Step 1: Create Google Sheets Version of Your Excel File

1. **Upload to Google Drive:**
   - Go to [Google Drive](https://drive.google.com)
   - Upload your existing timesheet workbook (Excel)
   - Right-click the uploaded file → "Open with" → "Google Sheets"
   - This converts it to Google Sheets format

2. **Get the Spreadsheet ID:**
   - In Google Sheets, look at the URL: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`
   - Copy the `{SPREADSHEET_ID}` part (long string of letters/numbers)

## Step 2: Create Google Service Account

1. **Go to Google Cloud Console:**
   - Visit [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing one

2. **Enable APIs:**
   - Go to "APIs & Services" → "Library"
   - Enable "Google Sheets API"
   - Enable "Google Drive API"

3. **Create Service Account:**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "Service Account"
   - Name it "timesheet-app" (or similar)
   - Click "Create and Continue"
   - Skip role assignment for now
   - Click "Done"

4. **Generate Key:**
   - Click on your new service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create New Key"
   - Choose "JSON" format
   - Download the JSON file

## Step 3: Share Google Sheets with Service Account

1. **Get Service Account Email:**
   - Open the downloaded JSON file
   - Find the "client_email" field
   - Copy this email address

2. **Share Your Google Sheets:**
   - Open your Google Sheets file
   - Click "Share" button
   - Add the service account email as an "Editor"
   - Uncheck "Notify people"
   - Click "Send"

## Step 4: Configure Streamlit Secrets

1. **Create/Edit `.streamlit/secrets.toml`:**
   ```toml
   # Google Sheets Configuration
   google_sheets_id = "YOUR_SPREADSHEET_ID_HERE"

   [google_sheets]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
   client_email = "timesheet-app@your-project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/timesheet-app%40your-project.iam.gserviceaccount.com"
   universe_domain = "googleapis.com"
   ```

2. **Copy values from your JSON file to secrets.toml**

## Step 5: Deploy and Test

1. **Commit and push your changes:**
   ```bash
   git add .
   git commit -m "Add Google Sheets integration"
   git push
   ```

2. **Configure Streamlit Cloud Secrets:**
   - Go to your Streamlit Cloud app settings
   - Add the same secrets from your local `secrets.toml`

3. **Test the integration:**
   - Your app should now read from Google Sheets
   - Make changes in Google Sheets - they appear in seconds!

## Benefits

✅ **Real-time updates** - Changes appear immediately
✅ **No git commands** - Edit directly in Google Sheets
✅ **Multiple users** - Team can edit simultaneously
✅ **Version history** - Google Sheets tracks all changes
✅ **Mobile friendly** - Edit from phone/tablet
✅ **Permissions** - Control who can view/edit

## Troubleshooting

- **"Credentials not found"** → Check secrets.toml configuration
- **"Permission denied"** → Make sure service account has access to your sheet
- **"Sheet not found"** → Verify spreadsheet ID and worksheet names match exactly