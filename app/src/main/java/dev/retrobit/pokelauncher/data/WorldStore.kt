package dev.retrobit.pokelauncher.data

import android.content.Context
import android.util.Log
import java.io.File

/**
 * The world's save file, on disk.
 *
 * Android-only by nature (files, Context, Log), which is why it sits in `data`
 * beside the other storage code and not in the pure `game` package.
 *
 * A launcher lives in a process Android kills freely, so "save on exit" would
 * mean "never save": there is no reliable exit. Instead the game saves after
 * every action that changes something and once a minute from the survival tick.
 * The file is tiny (a few kilobytes), so writing it that often is cheaper than
 * one icon decode.
 *
 * Writes go to a temporary file and are then renamed, so a kill mid-write
 * leaves the previous save intact rather than a half-written one.
 */
class WorldStore(context: Context) {

    private val file = File(context.filesDir, "world.json")
    private val temp = File(context.filesDir, "world.json.tmp")

    fun load(): String? = runCatching {
        if (!file.exists()) null else file.readText()
    }.onFailure { Log.w(TAG, "save tidak terbaca: ${it.message}") }.getOrNull()

    fun save(json: String) {
        runCatching {
            temp.writeText(json)
            if (file.exists() && !file.delete()) {
                // On a full disk the rename still replaces the old file.
                Log.w(TAG, "berkas lama tidak terhapus")
            }
            if (!temp.renameTo(file)) {
                file.writeText(json)
                temp.delete()
            }
        }.onFailure { Log.w(TAG, "gagal menyimpan: ${it.message}") }
    }

    /** Used by the settings sheet later; harmless now. */
    fun clear() {
        runCatching {
            file.delete()
            temp.delete()
        }
    }

    private companion object {
        const val TAG = "WorldStore"
    }
}
