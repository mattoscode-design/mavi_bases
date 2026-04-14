// ── Form de upload principal ──────────────────────────────────────────────────

// Hook do autocomplete: preenche o campo nome_varejista quando seleciona
function onVarejistaSelecionado(cod, nome) {
  document.getElementById("nome-varejista-hidden").value = nome.toLowerCase();
}

function submeterUpload() {
  const cod  = document.getElementById("cod-varejista-hidden").value;
  const nome = document.getElementById("nome-varejista-hidden").value;

  if (!cod || !nome) {
    alert("Selecione um varejista da lista antes de continuar.");
    return;
  }
  const arquivo = document.getElementById("arquivo").files[0];
  if (!arquivo) {
    alert("Selecione um arquivo antes de continuar.");
    return;
  }

  const btn = document.getElementById("btn-enviar");
  btn.textContent = "Processando...";
  btn.disabled    = true;

  document.getElementById("form-upload").submit();
}