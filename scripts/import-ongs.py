"""
Converte o CSV do Mapa das OSCs em arquivos prontos para uso no DoaZap.

Uso:
    python scripts/import-ongs.py <caminho_para_oscs_microdados.csv> [--limite N]

Saída (pasta data/):
    data/oscs_<UF>.csv     — um CSV por estado com as colunas do modelo Ong
    data/oscs_todos.csv    — CSV consolidado com todos os estados

As colunas geradas correspondem diretamente ao modelo Ong do banco de dados:
    name, category, subcategory, city, state, phone, email, website,
    pix_key, bank_info, description, is_active
"""

import argparse
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Caminhos relativos ao projeto (independente de onde o script é executado)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"

# Mapeamento de colunas do CSV original → modelo Ong
_COL_MAP = {
    "Nome da OSC": "name",
    "Area de Atuacao Principal": "category",
    "Subarea de Atuacao": "subcategory",
    "Municipio": "city",
    "UF": "state",
    "Telefone": "phone",
    "Email": "email",
    "Site": "website",
}

_ESTADOS_BRASIL = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "csv",
        help="Caminho para o arquivo oscs_microdados.csv (baixado do Mapa das OSCs)",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=10,
        metavar="N",
        help="Máximo de registros por estado (padrão: 10). Use 0 para sem limite.",
    )
    return parser.parse_args()


def _load_csv(path: str) -> pd.DataFrame:
    print(f"Lendo {path} …")
    df = pd.read_csv(path, dtype=str, low_memory=False)
    print(f"  {len(df):,} registros carregados. Colunas: {df.columns.tolist()}")
    return df


def _check_columns(df: pd.DataFrame) -> None:
    missing = [col for col in _COL_MAP if col not in df.columns]
    if missing:
        print(
            f"\n[AVISO] Colunas não encontradas no CSV: {missing}\n"
            "  Verifique se o arquivo é do Mapa das OSCs e ajuste _COL_MAP se necessário."
        )


def _prepare_state(df: pd.DataFrame, uf: str, limite: int) -> pd.DataFrame | None:
    df_uf = df[df["UF"] == uf].copy()
    if df_uf.empty:
        return None

    # Renomeia as colunas presentes (ignora ausentes silenciosamente)
    col_map: dict[str, str] = {k: v for k, v in _COL_MAP.items() if k in df_uf.columns}
    cols_out = list(col_map.values())
    df_uf = df_uf.rename(columns=col_map)[cols_out]  # type: ignore[call-overload]

    # Colunas extras que o modelo Ong espera mas não estão no CSV de origem
    for col in ("pix_key", "bank_info", "description"):
        if col not in df_uf.columns:
            df_uf[col] = ""
    df_uf["is_active"] = True

    if limite > 0:
        df_uf = df_uf.head(limite)

    return df_uf


def main() -> None:
    args = _parse_args()
    df = _load_csv(args.csv)
    _check_columns(df)

    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []

    for uf in _ESTADOS_BRASIL:
        df_uf = _prepare_state(df, uf, args.limite)
        if df_uf is None:
            print(f"  {uf}: nenhum registro encontrado — pulando")
            continue

        out_path = _DATA_DIR / f"oscs_{uf}.csv"
        df_uf.to_csv(out_path, index=False, encoding="utf-8-sig")
        frames.append(df_uf)
        print(f"  {uf}: {len(df_uf)} registros → {out_path.relative_to(_PROJECT_ROOT)}")

    if frames:
        consolidated = pd.concat(frames, ignore_index=True)
        out_all = _DATA_DIR / "oscs_todos.csv"
        consolidated.to_csv(out_all, index=False, encoding="utf-8-sig")
        print(f"\nConsolidado: {len(consolidated)} registros → {out_all.relative_to(_PROJECT_ROOT)}")
    else:
        print("\nNenhum registro gerado. Verifique a coluna 'UF' no CSV de entrada.")

    print("\nConcluído!")


if __name__ == "__main__":
    main()
