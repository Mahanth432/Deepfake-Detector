# Gmail SMTP Email Configuration - Setup Guide

## Overview

The Deepfake Detection AI application uses Gmail SMTP to send OTP (One-Time Password) verification emails during:
- User Registration
- Password Reset
- Account Verification

## Prerequisites

You need a Google account with:
- 2-Step Verification enabled
- Gmail access

## Step-by-Step Setup

### 1. Enable 2-Step Verification

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. In the left sidebar, click **"2-Step Verification"**
3. Click **"Get Started"**
4. Follow Google's prompts to:
   - Enter your phone number
   - Verify the code sent to your phone
   - Accept the terms

### 2. Generate Gmail App Password

**Important:** App Passwords only work with 2-Step Verification enabled.

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. You may need to sign in again
3. In the **"Select app"** dropdown, choose **"Mail"**
4. In the **"Select device"** dropdown, choose **"Windows Computer"** (or your device type)
5. Click **"Generate"**
6. Google will display a 16-character password (format: `xxxx xxxx xxxx xxxx`)
7. **Copy this password** - you'll use it in the next step

### 3. Configure Backend Environment Variables

1. Open `.env` file in your project root:
   ```
   c:\Users\nagan\OneDrive\Desktop\deepfake-detection-vit\.env
   ```

2. Fill in the email credentials:
   ```
   EMAIL_USER=your-gmail-address@gmail.com
   EMAIL_PASS=xxxx-xxxx-xxxx-xxxx
   ```

   Example:
   ```
   EMAIL_USER=john.doe@gmail.com
   EMAIL_PASS=abcd efgh ijkl mnop
   ```

   **Notes:**
   - `EMAIL_USER`: Your full Gmail address
   - `EMAIL_PASS`: The 16-character App Password (without or with spaces - both work)
   - Leave `MAIL_FROM` blank for auto-configuration

3. Save the `.env` file

### 4. Verify Configuration

Start the backend and check for the startup message:

```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
2026-05-08 22:01:48 - backend.app - INFO - Email service: Email configuration is valid.
```

If you see a warning:
```
WARNING: Missing required environment variables: EMAIL_USER, EMAIL_PASS
```

It means the `.env` file wasn't loaded properly. Check:
1. The `.env` file is in the project root (not in `backend/`)
2. The file has the correct variable names
3. No extra spaces or special characters

## Troubleshooting

### "Email authentication failed. Please check your Gmail App Password."

**Causes:**
- App Password is incorrect
- You're using your regular Gmail password instead of App Password
- 2-Step Verification is not enabled
- Spaces in the App Password weren't removed

**Solution:**
1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Generate a new App Password
3. Make sure you're using the 16-character App Password, not your Gmail password
4. Update `.env` file and restart the backend

### "Unable to connect to email server"

**Causes:**
- Network connectivity issue
- Gmail SMTP is blocked by firewall
- Incorrect SMTP server settings

**Solution:**
1. Verify `MAIL_SERVER=smtp.gmail.com` and `MAIL_PORT=587` in `.env`
2. Check your internet connection
3. If behind a corporate firewall, contact your IT administrator

### OTP email not received

**Check:**
1. Verify `.env` configuration is correct
2. Check spam/junk folder in Gmail
3. Look at backend logs for any error messages
4. Try sending another OTP after a few seconds

## Testing OTP Email Flow

### Register with OTP

1. Start the frontend: `npm run dev`
2. Go to Register page
3. Fill in credentials and click "Register"
4. You should receive an OTP email
5. Enter the 6-digit code in the modal
6. Click "Confirm OTP"

### Forgot Password

1. Go to Login page
2. Click "Forgot Password?"
3. Enter your email
4. You should receive an OTP email
5. Enter the 6-digit code
6. Set a new password

### Reset Password

1. Complete the Forgot Password flow above
2. Set a new password
3. Login with the new password

## Security Notes

- ⚠️ **Never** commit `.env` file to Git (it's in `.gitignore`)
- ⚠️ **Never** share your App Password publicly
- ⚠️ **Never** hardcode credentials in source code
- The App Password is only for your application and can be revoked anytime
- Each time you revoke the password, generate a new one

## File Reference

- **`.env`** - Your actual credentials (not committed to Git)
- **`.env.example`** - Template with instructions
- **`backend/email_service.py`** - Email sending logic
- **`backend/app.py`** - OTP endpoints (register, forgot password, reset)
- **`frontend/src/pages/Register.jsx`** - Registration with OTP
- **`frontend/src/pages/Login.jsx`** - Forgot password with OTP

## Support

If you encounter issues:

1. Check the backend logs for detailed SMTP error messages
2. Verify all credentials in `.env` are correct
3. Make sure 2-Step Verification is enabled on your Google Account
4. Try generating a new App Password
5. Restart both backend and frontend servers

## Next Steps

1. ✅ Enable 2-Step Verification
2. ✅ Generate App Password
3. ✅ Configure `.env` file
4. ✅ Restart backend server
5. ✅ Test OTP email sending
