# 📱 InstaAuto • Android Instagram Follower-Gated DM Automator

A self-hosted Instagram comment-to-DM automation app built to run **24/7 locally on your Android phone** with **100% UI control**. 

**You never need to touch or modify any code files.** Everything (Instagram login, 2FA authentication, API keys, trigger keywords, secret links, and DM templates) is configured directly inside the app interface.

---

## ⚡ How It Works

1. **Trigger on Keywords**: Whenever a user comments on your posts or reels with your chosen keywords (e.g., `link`, `send`, `guide`, `free`).
2. **Verifies Follower Status**: The bot checks whether the commenter is actively following your account.
3. **Protects Your Link**:
   - **If they are a FOLLOWER:** It delivers the link to their DMs and replies to their comment.
   - **If they DO NOT follow you:** It **blocks the link** and automatically replies to their comment explaining they must follow @youraccount first and comment again—driving organic follower growth!
4. **Active 24/7**: Operates as an Android **Foreground Service** with CPU wake-lock so Android OS never sleeps or kills the app when your screen is locked.

---

## 🚀 Two Ways to Install & Run (Zero Code Editing)

### 🌟 Option 1: Native Android APK (Standard Installable `.apk`)

The project includes a complete native Android Studio app (`android_apk/`) equipped with a **1-click GitHub Actions automatic APK builder**.

#### How to get your `.apk` in 60 seconds:
1. Create a GitHub repository (public or private) and push this project folder:
   ```bash
   git init
   git add .
   git commit -m "Initial InstaAuto App"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```
2. Open your repository on GitHub and tap the **Actions** tab.
3. The **"Build Android APK"** workflow runs automatically on GitHub's cloud runners (with Android SDK & Java 17).
4. When finished (~1 minute), click on the build run and download **`InstaAuto-Android-APK`** directly to your Android phone!
5. Tap the `.apk` on your phone to install it.

#### Inside the APK:
- **Account Screen**: Enter your Instagram username and password (or API Key / Access Token) and tap **Connect**. If 2FA is enabled, enter your 6-digit code.
- **Campaign Screen**: Type your trigger keywords (e.g., `link, send`), your secret URL, and your messages.
- **Start Button**: Tap **▶ Start Automator 24/7**. The app shows a persistent notification in your status bar and runs continuously in the background!

---

### 🌐 Option 2: 1-Tap WebAPK / PWA (Instant Android App via Termux)

If you don't want to build an APK on GitHub and prefer launching directly on your phone:

1. In Termux, run:
   ```bash
   chmod +x termux_install.sh start.sh stop.sh
   ./termux_install.sh
   ./start.sh
   ```
2. Open **Chrome** on your Android phone and navigate to:
   ```
   http://localhost:8080
   ```
3. Chrome will automatically display the **"Install App"** banner (or tap the 3 dots menu in Chrome > **Install app** / **Add to Home screen**).
4. **InstaAuto** will install directly onto your Android home screen as an app icon!
5. Open it from your home screen. You get the full standalone dark-mode app with:
   - **In-App Instagram Login & 2FA Modal** (no terminal login needed!).
   - **Keywords & Link Editor** (no editing `config.yaml`!).
   - **One-Tap Start/Stop Button**.
   - **Live stats & real-time comment logs**.

---

## 🎛️ Everything Handled in the UI (No Code Changes)

| Setting | Managed In UI? | Description |
| :--- | :---: | :--- |
| **Instagram Login** | ✅ | Enter username/password directly in UI; 2FA popup handles OTP codes |
| **API Key / Token** | ✅ | Optional field to input Meta Graph API token or RapidAPI key |
| **Trigger Keywords** | ✅ | Comma-separated list (e.g. `link, send, guide`) |
| **Follower DM Link** | ✅ | Customize your secret link and Spintax (`{Hey\|Hi} @{username}`) |
| **Follower Reply** | ✅ | Public comment reply confirming DM delivery |
| **Non-Follower Reply**| ✅ | Comment reply protecting the link and prompting them to follow |
| **Target Reel / Post** | ✅ | Paste specific Reel link or leave empty to auto-scan latest posts |
| **Daily DM Limit** | ✅ | Daily safety cap (default 50 DMs) to prevent Instagram rate-limits |
| **Scan Interval** | ✅ | Frequency of checking posts (default 60 seconds) |

---

## 🔋 Android 24/7 Execution (Anti-Sleep Settings)

To ensure Android never pauses or kills the automator in the background:

1. **Android Battery Optimization**:
   - Go to **Settings** > **Apps** > **InstaAuto** (or **Termux**).
   - Tap **Battery** > Select **Unrestricted** (Don't optimize).
2. **Autostart Permission** *(Xiaomi / Samsung / OnePlus / Oppo)*:
   - Go to App Info > Enable **Autostart**.
   - In Recent Apps screen, tap and hold the app and tap the **Lock 🔒** icon.
