package com.instaauto.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.instaauto.app.databinding.ActivityMainBinding
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val prefs by lazy { getSharedPreferences("InstaAutoPrefs", Context.MODE_PRIVATE) }
    private lateinit var engine: InstagramEngine

    private val logReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            intent?.let {
                val log = it.getStringExtra("log") ?: return
                val currentText = binding.tvLogs.text.toString()
                binding.tvLogs.text = "$log\n$currentText"

                binding.tvStatDMs.text = it.getIntExtra("dms", 0).toString()
                binding.tvStatFollowers.text = it.getIntExtra("followers", 0).toString()
                binding.tvStatBlocked.text = it.getIntExtra("blocked", 0).toString()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        engine = InstagramEngine(this)

        setupTabs()
        loadSavedSettings()
        setupButtons()
        setupWebViewLogin()
        updateConnectionUI()
        updateServiceUI()
    }

    private fun setupTabs() {
        binding.tabAutomator.setOnClickListener { switchTab(0) }
        binding.tabAccount.setOnClickListener { switchTab(1) }
        binding.tabLogs.setOnClickListener { switchTab(2) }
    }

    private fun switchTab(tabIndex: Int) {
        val activeBg = ContextCompat.getColor(this, R.color.accent_blue)
        val inactiveBg = ContextCompat.getColor(this, R.color.card_dark)
        val activeText = ContextCompat.getColor(this, R.color.text_primary)
        val inactiveText = ContextCompat.getColor(this, R.color.text_secondary)

        binding.scrollAutomationTab.visibility = if (tabIndex == 0) View.VISIBLE else View.GONE
        binding.scrollAccountTab.visibility = if (tabIndex == 1) View.VISIBLE else View.GONE
        binding.scrollLogsTab.visibility = if (tabIndex == 2) View.VISIBLE else View.GONE

        binding.tabAutomator.setBackgroundColor(if (tabIndex == 0) activeBg else inactiveBg)
        binding.tabAutomator.setTextColor(if (tabIndex == 0) activeText else inactiveText)

        binding.tabAccount.setBackgroundColor(if (tabIndex == 1) activeBg else inactiveBg)
        binding.tabAccount.setTextColor(if (tabIndex == 1) activeText else inactiveText)

        binding.tabLogs.setBackgroundColor(if (tabIndex == 2) activeBg else inactiveBg)
        binding.tabLogs.setTextColor(if (tabIndex == 2) activeText else inactiveText)
    }

    private fun setupButtons() {
        // Save Automation Rules
        binding.btnSaveConfig.setOnClickListener {
            saveSettings()
            Toast.makeText(this, "💾 Automation rules saved successfully!", Toast.LENGTH_SHORT).show()
        }

        // Main 24/7 Toggle Button
        binding.btnToggleBot.setOnClickListener {
            if (AutomationService.isRunning) {
                stopAutomationService()
            } else {
                // HARD CHECK: Do not allow starting without connected account
                if (!engine.isConnected()) {
                    MaterialAlertDialogBuilder(this)
                        .setTitle("⚠️ Instagram Account Required")
                        .setMessage("You cannot start the automator without connecting an Instagram account first.\n\nPlease log in via Web or Credentials in the Account tab.")
                        .setPositiveButton("Go to Login") { _, _ -> switchTab(1) }
                        .setNegativeButton("Cancel", null)
                        .show()
                    return@setOnClickListener
                }

                saveSettings()
                startAutomationService()
            }
        }

        // Credentials Login Button
        binding.btnLoginCredentials.setOnClickListener {
            val username = binding.etUsername.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            val twoFactor = binding.etTwoFactorCode.text.toString().trim()

            if (username.isBlank() || password.isBlank()) {
                Toast.makeText(this, "Please enter your Instagram username and password.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            binding.pbLoginProgress.visibility = View.VISIBLE
            binding.btnLoginCredentials.isEnabled = false

            lifecycleScope.launch {
                val result = engine.loginWithCredentials(username, password, twoFactor.ifBlank { null })
                binding.pbLoginProgress.visibility = View.GONE
                binding.btnLoginCredentials.isEnabled = true

                if (result.success) {
                    Toast.makeText(this@MainActivity, "✅ Connected as @${result.username}!", Toast.LENGTH_LONG).show()
                    updateConnectionUI()
                    switchTab(0) // Return to rules tab
                } else if (result.twoFactorRequired) {
                    MaterialAlertDialogBuilder(this@MainActivity)
                        .setTitle("🔐 2FA Code Required")
                        .setMessage("Instagram sent a 6-digit security code. Enter it in the 2FA box and tap Connect again.")
                        .setPositiveButton("OK", null)
                        .show()
                    binding.etTwoFactorCode.requestFocus()
                } else {
                    MaterialAlertDialogBuilder(this@MainActivity)
                        .setTitle("❌ Login Failed")
                        .setMessage(result.errorMessage)
                        .setPositiveButton("OK", null)
                        .show()
                }
            }
        }

        // Disconnect Account Button
        binding.btnDisconnectAccount.setOnClickListener {
            if (AutomationService.isRunning) {
                stopAutomationService()
            }
            engine.clearSession()
            CookieManager.getInstance().removeAllCookies(null)
            updateConnectionUI()
            Toast.makeText(this, "Account disconnected.", Toast.LENGTH_SHORT).show()
        }

        // Clear Logs Button
        binding.btnClearLogs.setOnClickListener {
            binding.tvLogs.text = "[Logs cleared]"
        }
    }

    private fun setupWebViewLogin() {
        binding.btnWebLogin.setOnClickListener {
            binding.layoutWebViewOverlay.visibility = View.VISIBLE
            binding.webViewInstagram.apply {
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                settings.userAgentString = "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

                val cookieManager = CookieManager.getInstance()
                cookieManager.setAcceptCookie(true)
                cookieManager.setAcceptThirdPartyCookies(this, true)

                webViewClient = object : WebViewClient() {
                    override fun onPageFinished(view: WebView?, url: String?) {
                        super.onPageFinished(view, url)
                        val cookies = cookieManager.getCookie("https://www.instagram.com") ?: ""
                        if (cookies.contains("sessionid=")) {
                            // Extract session credentials
                            var sessionId = ""
                            var dsUserId = ""
                            var csrfToken = ""

                            for (cookie in cookies.split(";")) {
                                val trimmed = cookie.trim()
                                if (trimmed.startsWith("sessionid=")) sessionId = trimmed.substringAfter("sessionid=")
                                if (trimmed.startsWith("ds_user_id=")) dsUserId = trimmed.substringAfter("ds_user_id=")
                                if (trimmed.startsWith("csrftoken=")) csrfToken = trimmed.substringAfter("csrftoken=")
                            }

                            if (sessionId.isNotBlank()) {
                                val username = binding.etUsername.text.toString().trim()
                                engine.saveSession(sessionId, dsUserId, csrfToken, username.ifBlank { "instagram_user" })
                                binding.layoutWebViewOverlay.visibility = View.GONE
                                updateConnectionUI()
                                Toast.makeText(this@MainActivity, "🎉 Connected successfully via Instagram Web!", Toast.LENGTH_LONG).show()
                                switchTab(0)
                            }
                        }
                    }
                }
                loadUrl("https://www.instagram.com/accounts/login/")
            }
        }

        binding.btnCloseWebView.setOnClickListener {
            binding.layoutWebViewOverlay.visibility = View.GONE
        }
    }

    private fun updateConnectionUI() {
        val isConnected = engine.isConnected()
        val username = engine.getConnectedUsername()

        if (isConnected) {
            binding.tvActiveAccountIndicator.text = if (username.isNotBlank()) "@$username" else "Connected"
            binding.tvActiveAccountIndicator.setTextColor(Color.parseColor("#00E676"))
            binding.tvConnectedUsername.text = if (username.isNotBlank()) "@$username" else "Connected Account"
            binding.tvConnectedDetails.text = "🟢 Active Instagram Session Connected"
            binding.btnDisconnectAccount.visibility = View.VISIBLE
            binding.tvToggleWarning.visibility = View.GONE
            binding.tvStatusBadge.text = if (AutomationService.isRunning) "ACTIVE 24/7" else "READY"
            binding.tvStatusBadge.setTextColor(Color.parseColor(if (AutomationService.isRunning) "#00E676" else "#FFB800"))
            binding.tvStatusBadge.setBackgroundColor(Color.parseColor(if (AutomationService.isRunning) "#3300E676" else "#33FFB800"))
        } else {
            binding.tvActiveAccountIndicator.text = "No Account Connected"
            binding.tvActiveAccountIndicator.setTextColor(Color.parseColor("#FF4D4D"))
            binding.tvConnectedUsername.text = "Not Connected"
            binding.tvConnectedDetails.text = "Please log in using Web or Credentials below"
            binding.btnDisconnectAccount.visibility = View.GONE
            binding.tvToggleWarning.visibility = View.VISIBLE
            binding.tvToggleWarning.text = "⚠️ Please connect your Instagram account first before starting."
            binding.tvStatusBadge.text = "DISCONNECTED"
            binding.tvStatusBadge.setTextColor(Color.parseColor("#FF4D4D"))
            binding.tvStatusBadge.setBackgroundColor(Color.parseColor("#33FF4D4D"))
        }
    }

    private fun updateServiceUI() {
        if (AutomationService.isRunning) {
            binding.btnToggleBot.text = "⏹ Stop Automator (Running 24/7)"
            binding.btnToggleBot.setBackgroundColor(Color.parseColor("#FF4D4D"))
            binding.tvStatusBadge.text = "ACTIVE 24/7"
            binding.tvStatusBadge.setTextColor(Color.parseColor("#00E676"))
            binding.tvStatusBadge.setBackgroundColor(Color.parseColor("#3300E676"))
        } else {
            binding.btnToggleBot.text = "▶ Start Automator 24/7"
            binding.btnToggleBot.setBackgroundColor(Color.parseColor("#00E676"))
            updateConnectionUI()
        }
    }

    private fun loadSavedSettings() {
        binding.etUsername.setText(prefs.getString("username", ""))
        binding.etKeywords.setText(prefs.getString("keywords", "link, send, guide, free, info"))
        binding.etFollowerDM.setText(
            prefs.getString(
                "follower_dm",
                "{Hey|Hi|Hello} @{username}! 👋 Here is your private link: https://yourlink.com/resource {Enjoy!|Hope this helps!}"
            )
        )
        binding.etNonFollowerReply.setText(
            prefs.getString(
                "non_follower_reply",
                "Hey @{username}! I can only send the link to followers. Please follow @{my_username} and comment again! 🙌"
            )
        )
        binding.etTargetPost.setText(prefs.getString("target_post", ""))
    }

    private fun saveSettings() {
        prefs.edit().apply {
            putString("username", binding.etUsername.text.toString().trim())
            putString("keywords", binding.etKeywords.text.toString().trim())
            putString("follower_dm", binding.etFollowerDM.text.toString().trim())
            putString("non_follower_reply", binding.etNonFollowerReply.text.toString().trim())
            putString("target_post", binding.etTargetPost.text.toString().trim())
            apply()
        }
    }

    private fun startAutomationService() {
        val intent = Intent(this, AutomationService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ContextCompat.startForegroundService(this, intent)
        } else {
            startService(intent)
        }
        AutomationService.isRunning = true
        updateServiceUI()
        Toast.makeText(this, "🚀 InstaAuto running 24/7 in background!", Toast.LENGTH_SHORT).show()
    }

    private fun stopAutomationService() {
        val intent = Intent(this, AutomationService::class.java)
        stopService(intent)
        AutomationService.isRunning = false
        updateServiceUI()
        Toast.makeText(this, "⏹ Automator Stopped", Toast.LENGTH_SHORT).show()
    }

    override fun onResume() {
        super.onResume()
        val filter = IntentFilter("com.instaauto.LOG_UPDATE")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(logReceiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(logReceiver, filter)
        }
        updateConnectionUI()
        updateServiceUI()
    }

    override fun onPause() {
        super.onPause()
        try {
            unregisterReceiver(logReceiver)
        } catch (e: Exception) {}
    }
}
