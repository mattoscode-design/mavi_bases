// ── Autocomplete de varejista ─────────────────────────────────────────────────
// Requerimentos no HTML:
//   <input id="inp-varejista" ...>
//   <input type="hidden" id="cod-varejista-hidden" name="cod_varejista">
//   <div id="sugestoes"></div>
//   window.VAREJISTAS = [{ cod: 1, nome: "Savegnago" }, ...]
//
// Hook opcional: defina onVarejistaSelecionado(cod, nome) na página
// para executar lógica extra após a seleção.

function filtrarVarejistas(texto) {
  const box = document.getElementById("sugestoes");
  document.getElementById("cod-varejista-hidden").value = "";

  if (!texto.trim()) { box.style.display = "none"; return; }

  const lista = (window.VAREJISTAS || []).filter(v =>
    v.nome.toLowerCase().includes(texto.toLowerCase())
  );

  if (!lista.length) { box.style.display = "none"; return; }

  box.innerHTML = lista.map(v => `
    <div onclick="selecionarVarejista(${v.cod}, '${v.nome}')"
         style="padding:8px 12px; cursor:pointer; font-size:14px;"
         onmouseover="this.style.background='var(--color-background-secondary)'"
         onmouseout="this.style.background=''">
      ${v.nome}
    </div>
  `).join("");
  box.style.display = "block";
}

function selecionarVarejista(cod, nome) {
  document.getElementById("inp-varejista").value        = nome;
  document.getElementById("cod-varejista-hidden").value = cod;
  document.getElementById("sugestoes").style.display    = "none";

  // hook para páginas com lógica extra
  if (typeof onVarejistaSelecionado === "function") {
    onVarejistaSelecionado(cod, nome);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const inp = document.getElementById("inp-varejista");
  if (inp) inp.addEventListener("input", () => filtrarVarejistas(inp.value));

  document.addEventListener("click", e => {
    if (!e.target.closest("#inp-varejista") && !e.target.closest("#sugestoes")) {
      const box = document.getElementById("sugestoes");
      if (box) box.style.display = "none";
    }
  });
});