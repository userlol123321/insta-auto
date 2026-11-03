package com.instaauto.app

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.random.Random

data class LoginResult(
    val success: Boolean,
    val twoFactorRequired: Boolean = false,
    val username: String = "",
    val userId: String = "",
    val errorMessage: String = ""
)

data class InstagramComment(
    val commentId: String,
    val userId: String,
    val username: String,
    val text: String
)

class InstagramEngine(private val context: Context) {

    private val prefs = context.getSharedPreferences("InstaAutoPrefs", Context.MODE_PRIVATE)

    private val client = OkHttpClient.Builder()
        .connectTimeout(25, TimeUnit.SECONDS)
        .readTimeout(25, TimeUnit.SECONDS)
        .followRedirects(true)
        .build()

    companion object {
        const val USER_AGENT = "Instagram 300.0.0.29.110 Android (33/13; 420dpi; 1080x2400; Xiaomi; 2201116SG; viva; mt6781; en_US; 513364962)"
    }

    fun isConnected(): Boolean {
        val sessionId = prefs.getString("session_id", "") ?: ""
        return sessionId.isNotBlank()
    }

    fun getConnectedUsername(): String {
        return prefs.getString("username", "") ?: ""
    }

    fun getConnectedUserId(): String {
        return prefs.getString("user_id", "") ?: ""
    }

    fun saveSession(sessionId: String, dsUserId: String, csrfToken: String, username: String) {
        prefs.edit().apply {
            putString("session_id", sessionId)
            putString("user_id", dsUserId)
            putString("csrf_token", csrfToken)
            if (username.isNotBlank()) putString("username", username)
            putBoolean("is_connected", true)
            apply()
        }
    }

    fun clearSession() {
        prefs.edit().apply {
            remove("session_id")
            remove("user_id")
            remove("csrf_token")
            putBoolean("is_connected", false)
            apply()
        }
    }

    private fun getCookieHeader(): String {
        val sessionId = prefs.getString("session_id", "") ?: ""
        val userId = prefs.getString("user_id", "") ?: ""
        val csrf = prefs.getString("csrf_token", "") ?: ""
        return "sessionid=$sessionId; ds_user_id=$userId; csrftoken=$csrf;"
    }

    /**
     * Direct HTTP login to Instagram
     */
    suspend fun loginWithCredentials(username: String, pass: String, twoFactorCode: String?): LoginResult = withContext(Dispatchers.IO) {
        try {
            val formBuilder = FormBody.Builder()
                .add("username", username)
                .add("enc_password", "#PWD_INSTAGRAM:0:${System.currentTimeMillis() / 1000}:$pass")
                .add("queryParams", "{}")
                .add("optIntoOneTap", "false")

            if (!twoFactorCode.isNullOrBlank()) {
                formBuilder.add("verification_code", twoFactorCode)
            }

            val request = Request.Builder()
                .url("https://i.instagram.com/api/v1/accounts/login/")
                .header("User-Agent", USER_AGENT)
                .header("X-IG-App-ID", "1217981644879628")
                .post(formBuilder.build())
                .build()

            val response = client.newCall(request).execute()
            val body = response.body?.string() ?: ""

            var sessionId = ""
            var dsUserId = ""
            var csrfToken = ""

            for (header in response.headers("Set-Cookie")) {
                if (header.contains("sessionid=")) {
                    sessionId = header.substringAfter("sessionid=").substringBefore(";")
                }
                if (header.contains("ds_user_id=")) {
                    dsUserId = header.substringAfter("ds_user_id=").substringBefore(";")
                }
                if (header.contains("csrftoken=")) {
                    csrfToken = header.substringAfter("csrftoken=").substringBefore(";")
                }
            }

            val json = try { JSONObject(body) } catch (e: Exception) { JSONObject() }

            if (json.optBoolean("two_factor_required", false)) {
                return@withContext LoginResult(
                    success = false,
                    twoFactorRequired = true,
                    username = username,
                    errorMessage = "Two-Factor Authentication required. Enter the 6-digit code."
                )
            }

            if (sessionId.isNotBlank()) {
                saveSession(sessionId, dsUserId, csrfToken, username)
                return@withContext LoginResult(
                    success = true,
                    username = username,
                    userId = dsUserId
                )
            }

            val message = json.optString("message", "Login failed. Check your username/password or use Web Login.")
            return@withContext LoginResult(success = false, errorMessage = message)

        } catch (e: Exception) {
            return@withContext LoginResult(success = false, errorMessage = "Network error: ${e.message}")
        }
    }

    /**
     * CRITICAL CHECK: Verifies if the commenter follows the account
     */
    suspend fun isUserFollowingMe(targetUserId: String): Boolean = withContext(Dispatchers.IO) {
        if (!isConnected()) return@withContext false
        try {
            val request = Request.Builder()
                .url("https://i.instagram.com/api/v1/friendships/show/$targetUserId/")
                .header("User-Agent", USER_AGENT)
                .header("Cookie", getCookieHeader())
                .header("X-IG-App-ID", "1217981644879628")
                .get()
                .build()

            val response = client.newCall(request).execute()
            val body = response.body?.string() ?: ""
            val json = JSONObject(body)

            // followed_by indicates whether targetUser follows authenticated account
            val followedBy = json.optBoolean("followed_by", false)
            Log.d("InstaAuto", "Follower check for $targetUserId: followed_by=$followedBy")
            return@withContext followedBy
        } catch (e: Exception) {
            Log.e("InstaAuto", "Error checking friendship status: ${e.message}")
            return@withContext false
        }
    }

    /**
     * Sends private direct message containing the link to verified followers
     */
    suspend fun sendDirectMessage(recipientUserId: String, messageText: String): Boolean = withContext(Dispatchers.IO) {
        if (!isConnected()) return@withContext false
        try {
            val jsonBody = JSONObject().apply {
                put("recipient_users", "[[${recipientUserId}]]")
                put("text", messageText)
                put("action", "send_item")
            }

            val request = Request.Builder()
                .url("https://i.instagram.com/api/v1/direct_v2/threads/broadcast/text/")
                .header("User-Agent", USER_AGENT)
                .header("Cookie", getCookieHeader())
                .header("Content-Type", "application/json")
                .post(jsonBody.toString().toRequestBody("application/json".toMediaType()))
                .build()

            val response = client.newCall(request).execute()
            return@withContext response.isSuccessful
        } catch (e: Exception) {
            Log.e("InstaAuto", "Failed sending DM: ${e.message}")
            return@withContext false
        }
    }

    /**
     * Posts a reply to a comment on a media post
     */
    suspend fun replyToComment(mediaId: String, commentId: String, text: String): Boolean = withContext(Dispatchers.IO) {
        if (!isConnected()) return@withContext false
        try {
            val form = FormBody.Builder()
                .add("comment_text", text)
                .add("replied_to_comment_id", commentId)
                .build()

            val request = Request.Builder()
                .url("https://i.instagram.com/api/v1/media/$mediaId/comment/")
                .header("User-Agent", USER_AGENT)
                .header("Cookie", getCookieHeader())
                .post(form)
                .build()

            val response = client.newCall(request).execute()
            return@withContext response.isSuccessful
        } catch (e: Exception) {
            Log.e("InstaAuto", "Failed replying to comment: ${e.message}")
            return@withContext false
        }
    }

    /**
     * Spintax Resolver: {Hey|Hi|Hello} -> random selection
     * Replaces {username}, {my_username}, {keyword}
     */
    fun renderSpintax(template: String, variables: Map<String, String>): String {
        var result = template
        val regex = Regex("\\{([^{}]+)\\}")
        while (regex.containsMatchIn(result)) {
            result = regex.replace(result) { match ->
                val content = match.groupValues[1]
                if (content.contains("|")) {
                    val choices = content.split("|")
                    choices[Random.nextInt(choices.size)].trim()
                } else {
                    "__VAR_${content}__"
                }
            }
        }
        for ((key, value) in variables) {
            result = result.replace("__VAR_${key}__", value)
            result = result.replace("{$key}", value)
        }
        return result.replace(Regex("__VAR_([a-zA-Z0-9_]+)__"), "")
    }

    /**
     * Keyword matching: checks if comment contains any trigger keywords
     */
    fun findMatchingKeyword(commentText: String, keywordsStr: String): String? {
        val keywords = keywordsStr.split(",").map { it.trim().lowercase() }.filter { it.isNotEmpty() }
        val lowerText = commentText.lowercase()
        for (kw in keywords) {
            if (lowerText.contains(kw)) {
                return kw
            }
        }
        return null
    }
}
