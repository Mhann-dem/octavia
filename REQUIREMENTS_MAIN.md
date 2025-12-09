# Octavia Web - Backend Integration Requirements

## Project Overview
We have a fully functional frontend built with Next.js and React. The goal of this phase is to connect this frontend to a robust backend system. You do not need to worry about UI design; your focus is on making the buttons work and integrating specific AI services.

## Core Integrations
You are required to use the following specific technologies for the backend services:

1.  **OpenAI Whisper**: Use this for all **Speech-to-Text** (transcription) tasks.
2.  **Helsinki NLP**: Use this for **Translation** tasks (text-to-text).
3.  **Coqui TTS**: Use this for **Text-to-Speech** (voice generation) tasks.
4.  **Polar.sh**: Use this for **Payments** and subscription management.

## Functional Requirements

### 1. Connect the Buttons
The frontend interface is ready. You need to wire up the existing buttons and forms to trigger the backend logic.
- **Video Translation**: When a user uploads a video and clicks "Translate", it should pipeline through Whisper -> Helsinki -> Coqui (if dubbing) or just generate subtitles.
- **Audio Translation**: Similar pipeline for audio files.
- **Subtitles**: Generate subtitles using Whisper.

### 2. User Accounts & Authentication
- **Signup Function**: Implement a working signup flow. Users must be able to create an account.
- **Login**: Connect the existing login forms to the backend authentication system.

### 3. Billing & Credits
- **Account Credit Function**: Implement a system for users to purchase and use credits.
- **Polar.sh Integration**: Use Polar.sh to handle the actual payments and credit purchases.

## Summary of Work
- **Frontend**: Provided (Done).
- **Backend**: You build this.
- **Stack**: OpenAI Whisper, Helsinki NLP, Coqui TTS, Polar.sh.
- **Key Actions**: Connect buttons, enable signup, enable payments.

This should be a straightforward integration task since the visual layer is already complete.

## Detailed Workflows (End-to-End)

### 1. Video Translation
1.  **Upload**: User uploads a video file via the dashboard.
2.  **Extraction**: Backend extracts the audio track from the video.
3.  **Transcription**: **OpenAI Whisper** transcribes the audio to text (source language).
4.  **Translation**: **Helsinki NLP** translates the text to the target language.
5.  **Dubbing**: **Coqui TTS** generates new audio from the translated text (matching the original voice if configured).
6.  **Merge**: Backend merges the new audio track with the original video.
7.  **Delivery**: User receives a notification and downloads the translated video.

### 2. Audio Translation
1.  **Upload**: User uploads an audio file.
2.  **Transcription**: **OpenAI Whisper** transcribes the audio to text.
3.  **Translation**: **Helsinki NLP** translates the text to the target language.
4.  **Synthesis**: **Coqui TTS** generates the spoken audio in the target language.
5.  **Delivery**: User plays or downloads the new audio file.

### 3. Subtitles
1.  **Upload**: User uploads a video or audio file.
2.  **Transcription**: **OpenAI Whisper** transcribes the audio, generating text with precise timestamps.
3.  **Formatting**: Backend formats the timestamped text into standard subtitle formats (SRT, VTT).
4.  **Delivery**: User views the subtitles in the editor or downloads the files.

### 4. Signup Function
1.  **Input**: User enters email and password on the Signup page.
2.  **Creation**: Backend validates input and creates a new user record in the database.
3.  **Verification**: System sends a verification email to the user.
4.  **Activation**: User clicks the link in the email; account status updates to "Active".
5.  **Access**: User is automatically logged in and redirected to the dashboard.

### 5. Account Credit Function
1.  **Selection**: User navigates to Billing and selects a credit package (e.g., "100 Credits").
2.  **Initiation**: App creates a pending transaction and redirects the user to the payment provider.
3.  **Processing**: Payment is processed securely (see Polar.sh below).
4.  **Fulfillment**: Upon success, the backend receives confirmation and adds credits to the user's balance.
5.  **Update**: User's dashboard updates to show the new credit total.

### 6. Polar.sh Payment Integration
1.  **Trigger**: User clicks "Buy" on a credit package.
2.  **API Call**: Backend calls the **Polar.sh API** to create a checkout session.
3.  **Redirect**: User is redirected to the secure Polar.sh checkout URL.
4.  **Payment**: User completes the payment on Polar.sh.
5.  **Webhook**: Polar.sh sends a webhook event (`payment.succeeded`) to the Octavia backend.
6.  **Verification**: Backend verifies the webhook signature to ensure authenticity.
7.  **Provisioning**: Backend updates the user's account with the purchased credits.
