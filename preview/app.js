/* PokeLauncher preview interaction.
 *
 * Every entry points at the PNG that tools/render_*.py produces, so the page
 * can never drift from the design: regenerate the images and reload.
 */
const SHOTS = {
  phone: {
    src: "../docs/preview-home.png",
    title: "Ponsel 412 dp",
    width: 824,
    height: 1784,
    layout: "Ponsel (< 700 dp): kartu pemain bertumpuk, tombol APLIKASI selebar kartu",
    chrome: "Tidak ditampilkan",
    note: "Grid 2 kolom, kartu pemain dua baris. Ini layout dasar yang juga dipakai " +
          "saat tablet dipegang tegak.",
    kind: "phone",
  },
  landscape: {
    src: "../docs/preview-tablet.png",
    title: "Tablet landscape 853 dp",
    width: 2628,
    height: 1668,
    layout: "Lebar (≥ 700 dp): kartu pemain satu baris, enam kartrid sejajar",
    chrome: "Bezel MatePad Mini, tanpa status bar",
    note: "Blok party di tengah, status card melebar, setelan jadi panel samping 380 dp. " +
          "Kamera punch-hole terlihat di kiri atas layar.",
    kind: "landscape",
  },
  portrait: {
    src: "../docs/preview-tablet-portrait.png",
    title: "Tablet portrait 533 dp",
    width: 1668,
    height: 2628,
    layout: "Sempit (< 700 dp): layout ponsel, grid 3 kolom",
    chrome: "Bezel MatePad Mini, tanpa status bar",
    note: "Penting: 533 dp ada di bawah ambang 700 dp, jadi saat tegak launcher memakai " +
          "layout ponsel, bukan layout tablet.",
    kind: "portrait",
  },
  "harmony-landscape": {
    src: "../docs/preview-harmonyos.png",
    title: "HarmonyOS landscape",
    width: 2628,
    height: 1668,
    layout: "Lebar (≥ 700 dp) dengan inset sistem",
    chrome: "Status bar 27 dp + gesture bar 16 dp",
    note: "Inset ikut menggeser konten seperti safeDrawingPadding(). Jam, wifi, sinyal, " +
          "baterai, dan pill gestur digambar meniru EMUI 13 / HarmonyOS 4.",
    kind: "landscape",
  },
  "harmony-portrait": {
    src: "../docs/preview-harmonyos-portrait.png",
    title: "HarmonyOS portrait",
    width: 1668,
    height: 2628,
    layout: "Sempit (< 700 dp) dengan inset sistem",
    chrome: "Status bar 27 dp + gesture bar 16 dp",
    note: "Jam status bar digeser ke kanan punch-hole, persis seperti EMUI menata ulang " +
          "ikon sistem di sekitar kamera.",
    kind: "portrait",
  },
};

const ORDER = ["phone", "landscape", "portrait", "harmony-landscape", "harmony-portrait"];

const stage = document.getElementById("stage");
const device = document.getElementById("device");
const shot = document.getElementById("shot");
const factsTitle = document.getElementById("facts-title");
const factsRes = document.getElementById("facts-res");
const factsLayout = document.getElementById("facts-layout");
const factsChrome = document.getElementById("facts-chrome");
const factsNote = document.getElementById("facts-note");
const openFull = document.getElementById("open-full");
const zoomToggle = document.getElementById("zoom-toggle");
const strip = document.getElementById("strip");

let current = "phone";

function render(key, { scroll = false } = {}) {
  const item = SHOTS[key];
  if (!item) return;
  current = key;

  shot.src = item.src;
  shot.alt = `Pratinjau PokeLauncher — ${item.title}`;
  device.classList.remove("is-zoomed");
  zoomToggle.textContent = "Perbesar 1:1";
  stage.className = `stage-media is-${item.kind}`;
  stage.parentElement.classList.toggle("is-landscape", item.kind === "landscape");

  factsTitle.textContent = item.title;
  factsRes.textContent = `${item.width} × ${item.height} px`;
  factsLayout.textContent = item.layout;
  factsChrome.textContent = item.chrome;
  factsNote.textContent = item.note;
  openFull.href = item.src;

  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab.dataset.key === key;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".thumb").forEach((thumb) => {
    thumb.classList.toggle("is-active", thumb.dataset.key === key);
  });

  const url = new URL(window.location.href);
  url.searchParams.set("layar", key);
  history.replaceState(null, "", url);

  if (scroll && window.innerWidth < 860) {
    document.getElementById("pratinjau").scrollIntoView({ block: "start" });
  }
}

function buildStrip() {
  ORDER.forEach((key) => {
    const item = SHOTS[key];
    const button = document.createElement("button");
    button.type = "button";
    button.className = "thumb";
    button.dataset.key = key;
    button.title = item.title;
    const img = document.createElement("img");
    img.src = item.src;
    img.alt = "";
    img.loading = "lazy";
    const label = document.createElement("span");
    label.textContent = item.title.replace(" 853 dp", "").replace(" 533 dp", "");
    button.append(img, label);
    button.addEventListener("click", () => render(key, { scroll: true }));
    strip.append(button);
  });
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => render(tab.dataset.key));
});

zoomToggle.addEventListener("click", () => {
  const zoomed = device.classList.toggle("is-zoomed");
  zoomToggle.textContent = zoomed ? "Kembalikan" : "Perbesar 1:1";
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
  const index = ORDER.indexOf(current);
  const next = event.key === "ArrowRight"
    ? (index + 1) % ORDER.length
    : (index - 1 + ORDER.length) % ORDER.length;
  render(ORDER[next]);
});

buildStrip();
const requested = new URLSearchParams(window.location.search).get("layar");
render(SHOTS[requested] ? requested : "phone");
