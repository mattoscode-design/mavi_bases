// ── Validação de lojas pendentes ──────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".btn-vincular").forEach(btn => {
    btn.addEventListener("click", async () => {
      const row       = btn.dataset.row;
      const varejista = parseInt(btn.dataset.varejista);
      const nomeAlias = btn.dataset.nome;
      const sel       = document.querySelector(`#row-${row} .sel-loja`);
      const idLoja    = parseInt(sel.value);

      if (!idLoja) { alert("Selecione uma loja antes de salvar."); return; }

      const resp = await fetch("/validacao/vincular", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
          cod_varejista: varejista,
          nome_alias:    nomeAlias,
          id_loja:       idLoja,
        }),
      });

      const data = await resp.json();
      if (data.ok) {
        btn.style.display = "none";
        document.getElementById(`ok-${row}`).style.display = "inline";
        sel.disabled = true;
      } else {
        alert("Erro ao salvar: " + data.erro);
      }
    });
  });
});