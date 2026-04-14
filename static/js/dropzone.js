// ── Dropzone: upload com drag and drop ────────────────────────────────────────
// Requerimentos no HTML:
//   <div id="dropzone">...</div>
//   <input type="file" id="arquivo" ...>
//   <div class="dz-filename" id="dz-filename"></div>

function mostrarArquivo(input) {
  const nome = input.files[0]?.name || "";
  document.getElementById("dz-filename").textContent = nome;
  document.getElementById("dropzone").classList.add("has-file");
}

function handleDrop(e) {
  e.preventDefault();
  e.stopPropagation();
  document.getElementById("dropzone").classList.remove("drag");
  const file = e.dataTransfer.files[0];
  if (file) {
    const input = document.getElementById("arquivo");
    const dt    = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    mostrarArquivo(input);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const dz = document.getElementById("dropzone");
  if (!dz) return;

  dz.addEventListener("dragover",  e => { e.preventDefault(); dz.classList.add("drag"); });
  dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
  dz.addEventListener("drop",      handleDrop);
  dz.addEventListener("click",     e => {
    e.stopPropagation();
    e.preventDefault();
    document.getElementById("arquivo").click();
  });

  const input = document.getElementById("arquivo");
  if (input) input.addEventListener("change", () => mostrarArquivo(input));
});