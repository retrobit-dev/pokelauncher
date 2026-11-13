# PokeLauncher

Launcher Android native bergaya **Pokémon HeartGold / SoulSilver**: home screen pengganti dengan
enam slot "party", app drawer, jam HeartGold, dan setelan tampilan. Seluruh ilustrasi
(langit Johto, bukit, Poké Ball, kartrid GBA) digambar dari kode Compose — tanpa aset berhak cipta.

![PokeLauncher di MatePad Mini](docs/preview-tablet.png)

> Layar launcher di dalam bezel hitam **Huawei MatePad Mini** (8.8", 2560 × 1600, 343 ppi, bezel
> ~4.4 mm), landscape. PNG-nya RGBA: sudut bodi transparan sehingga bentuk tablet tetap terlihat
> di atas latar apa pun. Dibuat oleh `tools/render_tablet.py` dari palet asli
> `ui/theme/Theme.kt` dan tata letak `LauncherScreen.kt` — pratinjau desain, bukan render emulator.

### Perilaku di layar besar

| Lebar layar | Layout |
| --- | --- |
| < 700 dp | Kartu pemain bertumpuk (tombol APLIKASI selebar kartu), grid 2/3/4 kolom sesuai setelan |
| ≥ 700 dp | Kartu pemain satu baris dengan tombol di kanan, enam kartrid sejajar, blok party di tengah, status card satu baris, setelan jadi panel samping 380 dp |

### Huawei MatePad Mini (HarmonyOS 4.3)

HarmonyOS **4.3.0 masih berbasis AOSP dan melaporkan API 31 (Android 12)**, jadi APK Android
dipasang dan dijalankan native — tidak perlu HarmonyOS NEXT / AppGallery. Beberapa konsekuensinya:

| Hal | Perilaku di HarmonyOS 4.3 | Status di project |
| --- | --- | --- |
| minSdk / targetSdk | 26 / 35 | Aman: semua API yang dipakai ≤ API 31 |
| Ikon adaptive | didukung sejak API 26 | vector v26 + fallback PNG |
| Splash screen | memakai `values-v31` (windowSplashScreen*) | otomatis aktif |
| Ikon monokrom (tema) | hanya v33 | diabaikan, fallback ke ikon biasa |
| `ACTION_HOME_SETTINGS` | sering tidak tersedia di EMUI | dicoba berurutan: intent EMUI → AOSP → default apps → detail app; kalau semuanya gagal muncul panduan manual |
| Google Play Services | tidak ada | project tidak memakai GMS sama sekali |
| `predictive back` / `POST_NOTIFICATIONS` | API 33 | tidak dipakai (dijaga `tools/verify.py`) |

Cara paling cepat: menu **START → JADIKAN HOME DEFAULT → JADIKAN HOME**. Tombol itu memakai
`RoleManager.createRequestRoleIntent(ROLE_HOME)` (API 29+, tersedia di HarmonyOS 4.3) sehingga
dialog izin muncul langsung tanpa membuka Setelan. Kalau role manager tidak tersedia, aplikasi
jatuh ke intent Setelan EMUI; kalau itu juga tidak ada, muncul panduan manual di bawah.

Panduan manual jika dialog sistem tidak muncul: **Setelan → Aplikasi → Aplikasi default →
Aplikasi layar utama → PokeLauncher**, atau **Setelan → Aplikasi → PokeLauncher → Buka secara
default → Layar utama**, lalu tekan tombol Home.

MatePad Mini dipakai **landscape**: 853 dp, jadi selalu masuk layout lebar. Di portrait (533 dp)
launcher akan memakai layout ponsel, tetapi pratinjau di repo hanya menyajikan landscape.

---

## Isi repo

```
app/src/main/java/dev/retrobit/pokelauncher/
├── MainActivity.kt              Activity tunggal, entry point HOME
├── data/
│   ├── Models.kt                AppEntry, PartySlot, LauncherSettings, LauncherUiState
│   ├── PartyRules.kt            Aturan party 6 slot (murni Kotlin, ada unit test)
│   └── LauncherRepository.kt    PackageManager, prefs, cache ikon
├── ui/
│   ├── LauncherScreen.kt        Root: layar home kosong + semua modal
│   ├── LauncherViewModel.kt     StateFlow tunggal, semua I/O di Dispatchers.IO
│   ├── components/              HgPanel, HgButton, AppIcon, Pokeball, ikon vektor
│   ├── screens/                 App drawer, settings, menu sheet, app info, dialog
│   └── theme/                   Palet HeartGold + 3 font pixel
└── res/                         strings (id + en), tema, ikon adaptive
tools/                           Skrip verifikasi, render & server pratinjau
docs/                            Render MatePad Mini (landscape)
licenses/                        Lisensi OFL untuk font
```

## Cara build

Butuh Android Studio **Ladybug** (AGP 8.7) atau lebih baru, JDK 17.

```bash
# dari Android Studio: File > Open > folder ini, lalu Run
# atau dari terminal:
./gradlew assembleDebug        # APK debug di app/build/outputs/apk/debug/
./gradlew test                 # unit test PartyRules
./gradlew assembleRelease      # perlu signing config sendiri
```

`local.properties` (berisi `sdk.dir`) dibuat otomatis oleh Android Studio. Untuk build via CLI,
salin `local.properties.example` menjadi `local.properties` dan sesuaikan path SDK.

## Menjadikan launcher sebagai home screen

1. Install APK, buka aplikasinya sekali.
2. Tekan tombol **APLIKASI** lalu buka **Pengaturan → JADIKAN HOME DEFAULT**.
3. Di dialog sistem pilih **PokeLauncher**, lalu **Selalu**.

Di sebagian ROM (MIUI, ColorOS, One UI) dialog itu diganti halaman khusus: buka
*Settings → Apps → Default apps → Home app*. Jika perangkat gagal menampilkan dialog,
PokeLauncher otomatis membuka halaman info aplikasi sebagai fallback.

## Fitur

| Fitur | Detail |
| --- | --- |
| Party 6 slot | Favorit disimpan sebagai `package/activity`, bertahan setelah reboot & update. |
| Kartu kartrid | Kartrid GBA digambar per-langkah (`cartridgePath`), warna berbeda per slot. |
| Level | Naik dari jumlah peluncuran aplikasi (`1 + launches / 5`, maksimum 100). |
| App drawer | Pencarian instan, tambah/hapus party lewat Poké Ball, long-press untuk info. |
| Jam | `LaunchedEffect` bangun tepat di pergantian menit, tanpa wakelock. |
| App hilang | Slot menampilkan `???`; long-press untuk mengeluarkan dari party. |
| Layout adaptif | ≥700dp: pengaturan tampil sebagai panel samping, bukan layar penuh. |
| Lokalisasi | `values/` + `values-in/`, semua teks di `strings.xml`. |

## Keputusan teknis penting

- **Package visibility.** Android 11+ menyembunyikan aplikasi lain. Manifest mendeklarasikan
  `<queries><intent MAIN/LAUNCHER>` — bukan `QUERY_ALL_PACKAGES`, yang akan ditolak Play Store
  untuk launcher.
- **HOME intent filter** memakai `MAIN` + `HOME` + `DEFAULT`, `exported=true`,
  `stateNotNeeded=true`, `clearTaskOnLaunch=true`, `launchMode=singleTask`. Tanpa
  `stateNotNeeded` launcher bisa crash saat prosesnya dimatikan sistem.
- **Back tidak pernah menutup home.** Satu `BackHandler` aktif yang menutup layer teratas
  (dialog → sheet → drawer → settings) dan menelan tombol Back saat tidak ada layer, sehingga
  layar tidak pernah kosong.
- **Ikon dimuat di `Dispatchers.IO`** lewat `produceState`, lalu di-cache di `LruCache`. Cold start
  tidak memblokir frame pertama.
- **Tanpa simbol unicode di font pixel.** Press Start 2P/DotGothic16/Silkscreen tidak punya glyph
  `✕ ☰ ⚙ ⌕` (terbukti lewat pemeriksaan cmap font), jadi ikon digambar dengan `Canvas`.

## Verifikasi yang sudah dilakukan

Sandbox pengembangan tidak punya JDK/Android SDK dan akses Maven dibatasi, jadi build APK belum
dijalankan di sini. Sebagai gantinya ada dua skrip pemeriksaan deterministik:

```bash
python3 tools/static_check.py   # XML valid, referensi @resource, impor & delimiter Kotlin
python3 tools/verify.py         # alias version catalog, call-site Compose, kunci strings id/en
python3 tools/render_tablet.py   # regenerasi render MatePad Mini
python3 tools/preview_server.py  # halaman pratinjau di http://localhost:8000
```

Keduanya lulus tanpa error pada commit ini. Tetap jalankan `./gradlew assembleDebug` sekali di
mesin Anda; jika ada error kompilasi, kirimkan log-nya ke sesi ini untuk diperbaiki.

## Pratinjau interaktif (lokal)

Halaman pratinjau hanya menampilkan **satu render MatePad Mini landscape**, tanpa keterangan:

```bash
python3 tools/preview_server.py           # http://localhost:8000
python3 tools/preview_server.py --port 9000
```

Setelah `tools/render_tablet.py` dijalankan, cukup refresh browser. Server hanya menyajikan
`/docs/preview-tablet.png`; sisa repo tidak bisa diakses.

Punch hole kamera ada di **kiri atas** layar landscape: pada panel portrait hole-nya di sudut
kanan atas, dan memutar tablet ke landscape (searah jarum jam, tombol volume di atas) membawa
sudut itu ke kiri atas — sama seperti yang terlihat di foto perangkat sungguhan. `verify.py`
menjaga posisi dan ukurannya (sekitar 3-5% lebar panel) supaya tidak melenceng lagi.

## Build APK lewat GitHub Actions

Repo ini menyertakan `.github/workflows/android.yml`: setiap push ke branch mana pun akan
menjalankan `./gradlew assembleDebug` (dan unit test) di runner Ubuntu dengan JDK 17, lalu
mengunggah APK debug sebagai artifact. Untuk membuat build sekali klik:

1. Buka tab **Actions** → **Android build** → **Run workflow**, atau cukup push commit.
2. Setelah selesai, unduh APK dari salah satu jalur:
   - artifact **pokelauncher-debug** di halaman run (berisi `app-debug.apk`), atau
   - URL tetap: `https://github.com/retrobit-dev/pokelauncher/releases/download/apk-latest/pokelauncher-debug.apk`
     (prerelease `apk-latest` diperbarui otomatis setiap build sukses).
3. Salin APK ke tablet, izinkan *install unknown apps* (Setelan → Keamanan → Instal aplikasi tak dikenal),
   lalu pasang.

Build pertama sudah diverifikasi di CI: `BUILD SUCCESSFUL`, unit test `PartyRules` lulus, dan APK
berisi `classes.dex`, `resources.arsc`, `AndroidManifest.xml`, tiga font pixel, serta ikon adaptive.

Build release yang di-minify bisa dibuat lokal dengan `./gradlew assembleRelease` (butuh
keystore sendiri).

## Kredit & lisensi

- Kode: Apache-2.0 (lihat pemilik repo).
- Font: [Press Start 2P](https://fonts.google.com/specimen/Press+Start+2P),
  [DotGothic16](https://fonts.google.com/specimen/DotGothic16),
  [Silkscreen](https://fonts.google.com/specimen/Silkscreen) — SIL Open Font License 1.1,
  teks lisensi lengkap di `licenses/`.
- Pokémon adalah merek dagang Nintendo/Game Freak/Creatures. Repo ini tidak memuat aset Pokémon
  apa pun; gaya visualnya hanya berupa palet warna dan bentuk geometris.
