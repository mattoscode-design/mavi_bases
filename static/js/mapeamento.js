// ── Configuração de mapeamento de colunas ─────────────────────────────────────

let novasColunas = [];

const LABELS_ACAO = {
  "vazia":               "Coluna vazia",
  "valor_fixo":          "Valor fixo",
  "ano_atual":           "Ano atual (automático)",
  "calcular_quantidade": "Calcular QUANTIDADE",
};

// ── Colunas existentes ────────────────────────────────────────────────────────

function toggleRenomear(sel) {
  const col = sel.dataset.col;
  const inp = document.querySelector(`.inp-renomear[data-col="${CSS.escape(col)}"]`);
  if (!inp) return;

  // tipos que precisam mostrar campo de saída
  const comCampo = ["renomear", "separar_mes_ano", "cruzar_ean"];
  inp.style.display = comCampo.includes(sel.value) ? "inline-block" : "none";

  // ajusta placeholder conforme tipo
  if (sel.value === "separar_mes_ano") {
    inp.placeholder = "ex: MÊS|ANO";
    inp.title       = "Digite os nomes das colunas separados por | (ex: MÊS|ANO)";
  } else if (sel.value === "cruzar_ean") {
    inp.placeholder = "ex: SETOR_PRODUTO";
  } else {
    inp.placeholder = "novo nome...";
    inp.title       = "";
  }
}

// ── Colunas novas ─────────────────────────────────────────────────────────────

function toggleNovaFormula() {
  const sel = document.getElementById("sel-nova-acao").value;
  const inp = document.getElementById("inp-nova-formula");

  if (sel === "valor_fixo") {
    inp.style.display = "inline-block";
    inp.placeholder   = "ex: 2025";
  } else if (sel === "calcular_quantidade") {
    inp.style.display = "inline-block";
    inp.placeholder   = "ex: VALOR / Preço Unit";
  } else {
    inp.style.display = "none";
    inp.value         = "";
  }
}

function adicionarColuna() {
  const nome    = document.getElementById("inp-nova-col").value.trim();
  const tipo    = document.getElementById("sel-nova-acao").value;
  const formula = document.getElementById("inp-nova-formula").value.trim();

  if (!nome) { alert("Digite o nome da coluna."); return; }

  const idx = novasColunas.length;
  novasColunas.push({ coluna_entrada: null, coluna_saida: nome, tipo_acao: tipo, formula });

  let amostra = "—";
  if (tipo === "ano_atual")                amostra = new Date().getFullYear();
  else if (tipo === "valor_fixo")          amostra = formula || "—";
  else if (tipo === "calcular_quantidade") amostra = "calculado";

  const tbody = document.querySelector("#tabela-mapeamento tbody");
  const tr    = document.createElement("tr");
  tr.id       = `nova-main-${idx}`;
  tr.style.background = "var(--color-background-info)";
  tr.innerHTML = `
    <td>
      <strong>${nome}</strong>
      <span style="font-size:11px; color:var(--color-text-info); margin-left:6px;">nova</span>
    </td>
    <td style="font-size:12px; color:var(--color-text-secondary)">${amostra}</td>
    <td style="font-size:13px; color:var(--color-text-info)">${LABELS_ACAO[tipo] || tipo}</td>
    <td>
      <button type="button" class="btn-small"
              style="background:#e53e3e; border-color:#e53e3e"
              onclick="removerNova(${idx})">remover</button>
    </td>
  `;
  tbody.appendChild(tr);

  document.getElementById("inp-nova-col").value     = "";
  document.getElementById("inp-nova-formula").value = "";
}

function removerNova(idx) {
  novasColunas[idx] = null;
  const row = document.getElementById(`nova-main-${idx}`);
  if (row) row.remove();
}

// ── Salvar ────────────────────────────────────────────────────────────────────

async function salvarConfig() {
  const linhas  = document.querySelectorAll("#tabela-mapeamento tbody tr");
  const colunas = [];

  linhas.forEach(tr => {
    if (tr.id && tr.id.startsWith("nova-main-")) return;

    const sel       = tr.querySelector(".sel-acao");
    const inp       = tr.querySelector(".inp-renomear");
    if (!sel) return;

    const col       = sel.dataset.col;
    const tipo_acao = sel.value;
    const col_saida = inp ? inp.value.trim() : "";

    if (tipo_acao === "ignorar") return;

    colunas.push({
      coluna_entrada: col,
      coluna_saida:   col_saida || col,
      tipo_acao:      tipo_acao,
    });
  });

  novasColunas.filter(c => c !== null).forEach(c => colunas.push(c));

  const codVarejista = document.getElementById("cod-varejista-data").dataset.cod;

  const resp = await fetch("/mapeamento/salvar", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({
      cod_varejista: parseInt(codVarejista),
      colunas:       colunas,
    }),
  });

  const data = await resp.json();
  if (data.ok) {
    document.getElementById("msg-salvo").style.display = "inline";
    document.getElementById("msg-erro").style.display  = "none";
    setTimeout(() => {
      document.getElementById("msg-salvo").style.display = "none";
    }, 3000);
  } else {
    document.getElementById("msg-erro").textContent    = "Erro: " + data.erro;
    document.getElementById("msg-erro").style.display  = "inline";
    document.getElementById("msg-salvo").style.display = "none";
  }
}