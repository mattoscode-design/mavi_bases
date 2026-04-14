from engine.conexao import get_conexao


def carregar(cod_varejista: int) -> dict | None:
    """
    Carrega o mapeamento salvo no banco para o varejista.
    Retorna None se não houver mapeamento cadastrado.

    Estrutura retornada:
    {
        "renomear":    { "coluna_entrada": "coluna_saida" },
        "separar":     { "coluna_entrada": ["MES", "ANO"] },
        "cruzar_loja": { "coluna_id_direto": ..., "saida_id": ..., ... },
        "cruzar_ean":  { "coluna_ean": ..., "saida_setor": ... },
        "calcular":    { "coluna_saida": ("col_a", "/", "col_b") },
        "novas":       [{ "coluna_saida": ..., "tipo_acao": ..., "formula": ... }],
    }
    """
    try:
        conn = get_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT coluna_entrada, coluna_saida, tipo_acao, formula
            FROM mapeamento_colunas
            WHERE cod_varejista = %s
            ORDER BY ordem
            """,
            (cod_varejista,),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        return None

    if not rows:
        return None

    mapeamento = {
        "renomear": {},
        "separar": {},
        "cruzar_loja": {},
        "cruzar_ean": {},
        "calcular": {},
        "novas": [],
    }

    for row in rows:
        entrada = row["coluna_entrada"]
        saida = row["coluna_saida"] or ""
        tipo = row["tipo_acao"]
        formula = row.get("formula", "") or ""

        if tipo == "renomear" and entrada:
            mapeamento["renomear"][entrada] = saida

        elif tipo == "separar_mes_ano" and entrada:
            # coluna_saida armazena os dois nomes separados por |
            # ex: "MÊS|ANO"
            partes = saida.split("|") if "|" in saida else [saida, "ANO"]
            col_mes = partes[0].strip() if len(partes) > 0 else "MÊS"
            col_ano = partes[1].strip() if len(partes) > 1 else "ANO"
            mapeamento["separar"][entrada] = [col_mes, col_ano]

        # mantém compatibilidade com registros antigos separar_mes/separar_ano
        elif tipo == "separar_mes" and entrada:
            if entrada not in mapeamento["separar"]:
                mapeamento["separar"][entrada] = [saida, None]
            else:
                mapeamento["separar"][entrada][0] = saida

        elif tipo == "separar_ano" and entrada:
            if entrada not in mapeamento["separar"]:
                mapeamento["separar"][entrada] = [None, saida]
            else:
                mapeamento["separar"][entrada][1] = saida

        elif tipo == "id_loja" and entrada:
            mapeamento["cruzar_loja"] = {
                "coluna_id_direto": entrada,
                "coluna_matricula": None,
                "coluna_nome": None,
                "saida_id": "LOJA",
                "saida_nome": "BANCO",
            }

        elif tipo == "cruzar_ean" and entrada:
            mapeamento["cruzar_ean"] = {
                "coluna_ean": entrada,
                "saida_setor": saida or "SETOR_PRODUTO",
            }

        elif tipo == "calcular_quantidade" and entrada:
            partes = formula.split("/") if "/" in formula else []
            if len(partes) == 2:
                mapeamento["calcular"][saida] = (
                    partes[0].strip(),
                    "/",
                    partes[1].strip(),
                )

        elif tipo in ("vazia", "valor_fixo", "ano_atual") and not entrada:
            mapeamento["novas"].append(
                {
                    "coluna_saida": saida,
                    "tipo_acao": tipo,
                    "formula": formula,
                }
            )

    return mapeamento
