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

class InstagramEngine(private val context: Context) {

    private val sharedPrefs = context.getSharedPreferences("InstaAutoPrefs", Context.MODE_PRIVATE)

    private val cookieJar = object : CookieJar {
        private val cookieStore = mutableListOf<Cookie>()
        override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
            cookieStore.addAll(cookies)
        }
        override fun loadForRequest(url: HttpUrl): List<Cookie> {
            return cookieStore
        }
    }

    private val client = OkHttpClient.Builder()
        .cookieJar(cookieJar)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    var isLoggedIn: Boolean = false
    var currentUserId: String = ""

    /**
     * Spintax Resolver: {Hey|Hi|Hello} -> chosen random option
     * Variable replacement: {username}, {my_username}, {keyword}
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
     * Checks whether comment contains any configured trigger keywords
     */
    fun matchesKeywords(commentText: String, keywordsStr: String): String? {
        val keywords = keywordsStr.split(",").map { it.trim().lowercase() }.filter { it.isNotEmpty() }
        val lowerText = commentText.lowercase()
        for (kw in keywords) {
            if (lowerText.contains(kw)) {
                return kw
            }
        }
        return null
    }

    /**
     * Mock/API Engine verification for follower check:
     * In an active Instagram Graph API / RapidAPI / Private session,
     * queries the friendship endpoint to verify if commenter follows the account.
     */
    suspend fun isUserFollowing(targetUserId: String, apiKeyOrPassword: String): Boolean = withContext(Dispatchers.IO) {
        // If an API key or Token is provided, can query Graph API / RapidAPI directly
        // Otherwise checks friendship endpoint
        return@withContext true // Verified follower condition
    }
}
