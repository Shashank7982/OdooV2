# Fix: Wkhtmltopdf Not Found Error in Odoo 18

## Problem
Odoo cannot generate PDFs (quotations, invoices, reports) because Wkhtmltopdf is missing.

Error: `Unable to find Wkhtmltopdf on this system. The PDF can not be created.`

## Solution: Install Wkhtmltopdf

### Step 1: Download Wkhtmltopdf

Download the **Windows 64-bit installer** for wkhtmltopdf 0.12.6:

**Direct Download Link:**
```
https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox-0.12.6.1-3.msvc2015-win64.exe
```

Or visit manually:
1. Go to: https://github.com/wkhtmltopdf/packaging/releases
2. Find release **0.12.6-1** 
3. Download: `wkhtmltox-0.12.6.1-3.msvc2015-win64.exe`

### Step 2: Install Wkhtmltopdf

1. **Run the downloaded installer** (`wkhtmltox-0.12.6.1-3.msvc2015-win64.exe`)
2. **Accept the license agreement**
3. **Use the default installation path**: `C:\Program Files\wkhtmltopdf`
4. **Complete the installation**

### Step 3: Verify Installation

Open a **new** Command Prompt or PowerShell window and run:
```bash
wkhtmltopdf --version
```

Expected output:
```
wkhtmltopdf 0.12.6 (with patched qt)
```

**Important:** You must open a NEW terminal window for the PATH changes to take effect.

### Step 4: Configure Odoo (If Needed)

Odoo should automatically detect wkhtmltopdf. If it doesn't:

1. Open Odoo in your browser
2. Go to **Settings** → **Technical** → **System Parameters**
3. Add/Edit parameter:
   - **Key:** `report.wkhtmltopdf.path`
   - **Value:** `C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe`

### Step 5: Restart Odoo

After installation, restart your Odoo service:
```bash
# Stop Odoo (press Ctrl+C if running in terminal)
# Then restart it
python odoo-bin -c odoo.conf
```

### Step 6: Test PDF Generation

1. Go to Sales → Orders
2. Open any sales order
3. Click **Print** → **Quotation/Order**
4. The PDF should now generate successfully

## Alternative: Download via PowerShell

If you prefer to download via command line, run this in PowerShell:

```powershell
# Download wkhtmltopdf installer
$url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox-0.12.6.1-3.msvc2015-win64.exe"
$output = "$env:USERPROFILE\Downloads\wkhtmltox-installer.exe"
Invoke-WebRequest -Uri $url -OutFile $output
Write-Host "Downloaded to: $output"
Write-Host "Please run the installer to complete installation."
```

## Troubleshooting

### Issue: "wkhtmltopdf is not recognized..."
**Solution:** 
- Restart your terminal/IDE after installation
- Check if `C:\Program Files\wkhtmltopdf\bin` is in your PATH
- Manually add to PATH if needed:
  1. Search "Environment Variables" in Windows
  2. Edit System PATH
  3. Add: `C:\Program Files\wkhtmltopdf\bin`

### Issue: Odoo still shows error after installation
**Solution:**
1. Restart Odoo completely
2. Clear browser cache
3. Check System Parameters (see Step 4 above)

### Issue: PDF generates but has issues
**Solution:**
- Ensure you're using version 0.12.6 (not 0.12.5 or 0.13+)
- Version 0.12.6 is specifically recommended for Odoo

## Why This Error Occurs

Wkhtmltopdf is required by Odoo to convert HTML templates into PDF documents for:
- Sales quotations and orders
- Invoices
- Delivery slips
- Purchase orders
- Any other reports

The error occurs when:
1. Processing payment transactions that trigger order confirmation emails
2. Sending emails with PDF attachments
3. Manually generating PDF reports
4. Any automated process that creates PDFs

## Summary

✅ Download wkhtmltopdf 0.12.6 Windows installer
✅ Install to default location
✅ Verify with `wkhtmltopdf --version` in NEW terminal
✅ Restart Odoo
✅ Test PDF generation

After completing these steps, your Odoo system will be able to generate PDFs successfully.
