package com.instaauto.app

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*

class AutomationService : Service() {

    private val serviceJob = Job()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)
    private var wakeLock: PowerManager.WakeLock? = null
    private lateinit var engine: InstagramEngine

    companion object {
        const val CHANNEL_ID = "InstaAutoForegroundChannel"
        const val NOTIFICATION_ID = 1001
        var isRunning = false
        var dmsSentCount = 0
        var followersServedCount = 0
        var nonFollowersBlockedCount = 0
    }

    override fun onCreate() {
        super.onCreate()
        engine = InstagramEngine(this)
        createNotificationChannel()

        // Acquire WakeLock so CPU never sleeps
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "InstaAuto::BackgroundWakeLock"
        ).apply {
            acquire(24 * 60 * 60 * 1000L) // 24 hours lock
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        isRunning = true
        val notification = buildNotification("InstaAuto is running 24/7. Monitoring comments & DMs.")
        startForeground(NOTIFICATION_ID, notification)

        startAutomationLoop()

        return START_STICKY
    }

    private fun startAutomationLoop() {
        serviceScope.launch {
            val prefs = getSharedPreferences("InstaAutoPrefs", Context.MODE_PRIVATE)

            while (isActive && isRunning) {
                try {
                    val username = prefs.getString("username", "") ?: ""
                    val keywords = prefs.getString("keywords", "link, send") ?: "link, send"
                    val followerDm = prefs.getString("follower_dm", "") ?: ""
                    val nonFollowerReply = prefs.getString("non_follower_reply", "") ?: ""

                    broadcastLog("Scanning posts for keyword comments...")

                    // Delay between scan cycles
                    val interval = prefs.getInt("interval", 60) * 1000L
                    delay(interval)

                } catch (e: Exception) {
                    broadcastLog("Cycle warning: ${e.message}")
                    delay(30000L)
                }
            }
        }
    }

    private fun broadcastLog(message: String) {
        val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        val intent = Intent("com.instaauto.LOG_UPDATE").apply {
            putExtra("log", "[$time] $message")
            putExtra("dms", dmsSentCount)
            putExtra("followers", followersServedCount)
            putExtra("blocked", nonFollowersBlockedCount)
        }
        sendBroadcast(intent)
    }

    private fun buildNotification(text: String): Notification {
        val notificationIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, notificationIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("InstaAuto DM Active")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "InstaAuto 24/7 Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps Instagram comment automator alive in background"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        isRunning = false
        serviceJob.cancel()
        wakeLock?.let {
            if (it.isHeld) it.release()
        }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
