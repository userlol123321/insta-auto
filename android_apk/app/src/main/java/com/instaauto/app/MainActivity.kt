package com.instaauto.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.instaauto.app.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val prefs by lazy { getSharedPreferences("InstaAutoPrefs", Context.MODE_PRIVATE) }

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

        loadSavedSettings()

        binding.btnSaveConfig.setOnClickListener {
            saveSettings()
            Toast.makeText(this, "✅ Settings Saved! No code changes needed.", Toast.LENGTH_SHORT).show()
        }

        binding.btnToggleBot.setOnClickListener {
            if (AutomationService.isRunning) {
                stopAutomationService()
            } else {
                saveSettings()
                startAutomationService()
            }
        }

        updateUIState()
    }

    private fun loadSavedSettings() {
        binding.etUsername.setText(prefs.getString("username", ""))
        binding.etPassword.setText(prefs.getString("password", ""))
        binding.etKeywords.setText(prefs.getString("keywords", "link, send, guide, free"))
        binding.etFollowerDM.setText(
            prefs.getString(
                "follower_dm",
                "{Hey|Hi|Hello} @{username}! 👋 Here is your exclusive link: https://yourlink.com/resource {Enjoy!|Hope this helps!}"
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
            putString("password", binding.etPassword.text.toString().trim())
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
        updateUIState()
        Toast.makeText(this, "🚀 InstaAuto running 24/7 in background!", Toast.LENGTH_SHORT).show()
    }

    private fun stopAutomationService() {
        val intent = Intent(this, AutomationService::class.java)
        stopService(intent)
        AutomationService.isRunning = false
        updateUIState()
        Toast.makeText(this, "⏹ Automator Stopped", Toast.LENGTH_SHORT).show()
    }

    private fun updateUIState() {
        if (AutomationService.isRunning) {
            binding.tvStatusBadge.text = "ACTIVE 24/7"
            binding.tvStatusBadge.setTextColor(Color.parseColor("#3FB950"))
            binding.tvStatusBadge.setBackgroundColor(Color.parseColor("#332EA043"))
            binding.btnToggleBot.text = "⏹ Stop Automator"
            binding.btnToggleBot.setBackgroundColor(Color.parseColor("#DA3633"))
        } else {
            binding.tvStatusBadge.text = "STOPPED"
            binding.tvStatusBadge.setTextColor(Color.parseColor("#F85149"))
            binding.tvStatusBadge.setBackgroundColor(Color.parseColor("#33DA3633"))
            binding.btnToggleBot.text = "▶ Start Automator 24/7"
            binding.btnToggleBot.setBackgroundColor(Color.parseColor("#2EA043"))
        }
    }

    override fun onResume() {
        super.onResume()
        val filter = IntentFilter("com.instaauto.LOG_UPDATE")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(logReceiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(logReceiver, filter)
        }
        updateUIState()
    }

    override fun onPause() {
        super.onPause()
        try {
            unregisterReceiver(logReceiver)
        } catch (e: Exception) {}
    }
}
