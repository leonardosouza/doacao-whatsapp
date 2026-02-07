"""Importa ONGs do arquivo data/ONGS.json para o banco de dados."""

import logging
import re
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.ong import Ong

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "ONGS.json"


def parse_category(raw: str) -> tuple[str, str | None]:
    """Separa 'Saúde/Câncer Infantil' em ('Saúde', 'Câncer Infantil')."""
    if "/" in raw:
        parts = raw.split("/", 1)
        return parts[0].strip(), parts[1].strip()
    return raw.strip(), None


def parse_city_state(raw: str) -> tuple[str, str]:
    """Separa 'São Paulo - SP' em ('São Paulo', 'SP')."""
    match = re.match(r"(.+?)\s*-\s*(\w{2})", raw)
    if match:
        return match.group(1).strip(), match.group(2).strip().upper()
    # Trata casos especiais como 'São Paulo - SP (Base Pantanal)'
    match = re.match(r"(.+?)\s*-\s*(\w{2})\s*\(", raw)
    if match:
        return match.group(1).strip(), match.group(2).strip().upper()
    return raw.strip(), ""


def parse_contact(raw: str) -> tuple[str | None, str | None, str | None]:
    """Extrai website, telefone e email do campo Contato_Site."""
    website = None
    phone = None
    email = None

    parts = [p.strip() for p in raw.split("|")]
    for part in parts:
        if re.match(r"^\(?\d{2}\)?\s?\d{4}", part):
            phone = part
        elif "@" in part:
            email = part
        elif "." in part and not part.startswith("0"):
            website = part

    return website, phone, email


def parse_donation(raw: str) -> tuple[str | None, str | None, str | None]:
    """Extrai pix_key, bank_info e donation_url do campo Dados_Doacao."""
    pix_key = None
    bank_info = None
    donation_url = None

    if "Recomendado:" in raw or "Doar via Site" in raw:
        donation_url = raw.strip()
        return pix_key, bank_info, donation_url

    parts = [p.strip() for p in raw.split("|")]
    for part in parts:
        lower = part.lower()
        if lower.startswith("pix"):
            # Extrai a chave PIX após ":"
            match = re.search(r":\s*(.+)", part)
            if match:
                pix_key = match.group(1).strip()
        elif "banco" in lower or "ag:" in lower or "ag " in lower:
            bank_info = (bank_info + " | " + part) if bank_info else part
        elif "cnpj" in lower:
            bank_info = (bank_info + " | " + part) if bank_info else part
        elif lower.startswith("doação") or lower.startswith("doacao"):
            donation_url = part
        else:
            # Campo não classificado — tenta identificar como PIX ou bank
            if re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", part):
                pix_key = part  # CNPJ como PIX
            elif "@" in part:
                pix_key = part  # E-mail como PIX
            elif bank_info is None and pix_key is None:
                bank_info = part

    return pix_key, bank_info, donation_url


def seed(db: Session) -> int:
    """Lê ONGS.json e insere os registros no banco."""
    lines = DATA_FILE.read_text(encoding="utf-8").strip().splitlines()
    header = lines[0]  # Pula cabeçalho
    count = 0

    for line in lines[1:]:
        fields = line.split(";")
        if len(fields) < 5:
            logger.warning(f"Linha ignorada (campos insuficientes): {line}")
            continue

        name = fields[0].strip()
        category, subcategory = parse_category(fields[1])
        city, state = parse_city_state(fields[2])
        website, phone, email = parse_contact(fields[3])
        pix_key, bank_info, donation_url = parse_donation(fields[4])

        # Verifica se já existe
        existing = db.query(Ong).filter(Ong.name == name).first()
        if existing:
            logger.info(f"  Já existe: {name}")
            continue

        ong = Ong(
            name=name,
            category=category,
            subcategory=subcategory,
            city=city,
            state=state,
            phone=phone,
            website=website,
            email=email,
            pix_key=pix_key,
            bank_info=bank_info,
            donation_url=donation_url,
        )
        db.add(ong)
        count += 1
        logger.info(f"  + {name} ({category}/{subcategory or '-'}) — {city}/{state}")

    db.commit()
    return count


def main():
    logger.info(f"Lendo dados de {DATA_FILE}")
    db = SessionLocal()
    try:
        count = seed(db)
        logger.info(f"Seed concluído: {count} ONGs inseridas")
    finally:
        db.close()


if __name__ == "__main__":
    main()
