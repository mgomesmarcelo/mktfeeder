from __future__ import annotations

from datetime import date
from pathlib import Path
import pandas as pd

from src.mktfeeder_greyhounds.config import settings
from src.mktfeeder_greyhounds.logger import get_logger
from src.mktfeeder_greyhounds.utils.dates import today_str
from src.mktfeeder_greyhounds.utils.files import atomic_write_text, read_csv, write_dataframe
from src.mktfeeder_greyhounds.utils.text import normalize_category, normalize_spaces

logger = get_logger()


def _strategy_for_category(category_norm: str) -> tuple[str | None, float | None]:
    cat = normalize_category(category_norm)
    if any(cat.startswith(prefix) for prefix in settings.BACK_CATEGORY_PREFIXES):
        return "BACK", settings.STAKE_BACK
    if any(cat.startswith(prefix) for prefix in settings.LAY_CATEGORY_PREFIXES):
        return "LAY", settings.STAKE_LAY
    return None, None


def _format_line(track: str, hhmm: str, dog_name: str, strategy_tag: str, stake: float) -> str:
    dog = normalize_spaces(dog_name)
    return f"[{hhmm} {track}]{dog}\t\"{strategy_tag}\"\t{stake}"


def _load_today_forecast() -> pd.DataFrame:
    path = settings.OUTPUT_FORECAST_DIR / f"forecast_{today_str()}.csv"
    df = read_csv(path)
    if df.empty:
        logger.warning("FORECAST do dia vazio ou inexistente: {}", path)
    return df


def _build_lines_and_audit(
    df_forecast: pd.DataFrame,
) -> tuple[list[str], list[dict[str, object]], int, dict[str, int], dict[str, int], dict[str, int], int, dict[str, int]]:
    lines: list[str] = []
    audit_rows: list[dict[str, object]] = []
    skipped_forecast_incomplete = 0
    counts_by_strategy: dict[str, int] = {}
    races_by_strategy: dict[str, int] = {}
    exported_category_counts: dict[str, int] = {}
    ignored_by_category_total = 0
    ignored_category_counts: dict[str, int] = {}
    records: list[dict[str, object]] = []

    for _, row in df_forecast.iterrows():
        track = normalize_spaces(str(row.get("track") or ""))
        hhmm = str(row.get("hhmm") or "")
        category_norm = normalize_category(str(row.get("category_norm") or ""))
        category_raw = normalize_spaces(str(row.get("category_raw") or ""))
        strategy_tag, stake = _strategy_for_category(category_norm)
        if not strategy_tag or stake is None:
            ignored_by_category_total += 1
            ignored_category_counts[category_norm] = ignored_category_counts.get(category_norm, 0) + 1
            logger.debug("Corrida ignorada por categoria: {} {}", track, category_norm)
            continue

        dogs = [
            str(row.get("forecast_1") or "").strip(),
            str(row.get("forecast_2") or "").strip(),
            str(row.get("forecast_3") or "").strip(),
        ]
        if not dogs[0] or any(not d for d in dogs):
            logger.info("Corrida ignorada por forecast incompleto: {} {}", track, hhmm)
            skipped_forecast_incomplete += 1
            continue

        races_by_strategy[strategy_tag] = races_by_strategy.get(strategy_tag, 0) + 1
        if category_norm:
            exported_category_counts[category_norm] = exported_category_counts.get(category_norm, 0) + 1
        for order_idx, dog in enumerate(dogs):
            records.append(
                {
                    "track": track,
                    "hhmm": hhmm,
                    "category_raw": category_raw,
                    "category_norm": category_norm,
                    "dog_name": normalize_spaces(dog),
                    "strategy_tag": strategy_tag,
                    "stake": stake,
                    "order": order_idx,
                }
            )
            counts_by_strategy[strategy_tag] = counts_by_strategy.get(strategy_tag, 0) + 1

    # Ordena por horário e, em seguida, por track e ordem (Forecast1..3)
    sorted_records = sorted(records, key=lambda r: (r["hhmm"], r["track"], r["order"]))
    for rec in sorted_records:
        line = _format_line(rec["track"], rec["hhmm"], rec["dog_name"], rec["strategy_tag"], rec["stake"])
        lines.append(line)
        audit_rows.append(
            {
                "date": today_str(),
                "track": rec["track"],
                "hhmm": rec["hhmm"],
                "category_raw": rec["category_raw"],
                "category_norm": rec["category_norm"],
                "dog_name": rec["dog_name"],
                "strategy_tag": rec["strategy_tag"],
                "stake": rec["stake"],
            }
        )
    if settings.KEEP_ALL_ACTIVE:
        lines.append("#all_active#")
    return (
        lines,
        audit_rows,
        skipped_forecast_incomplete,
        counts_by_strategy,
        races_by_strategy,
        exported_category_counts,
        ignored_by_category_total,
        ignored_category_counts,
    )


def _write_marketfeeder_files(lines: list[str], audit_rows: list[dict[str, object]]) -> tuple[Path, Path, Path]:
    base_dir = settings.MARKETFEEDER_DIR
    hist_dir = settings.MARKETFEEDER_HISTORY_DIR
    today = today_str()

    fixed_path = base_dir / "import_selections.txt"
    tmp_path = base_dir / "import_selections.tmp"
    hist_txt = hist_dir / f"import_selections_{today}.txt"
    audit_csv = hist_dir / f"import_selections_{today}_audit.csv"

    content = "\n".join(lines)
    # escreve tmp e depois substitui o fixo
    atomic_write_text(tmp_path, content)
    if fixed_path.exists():
        fixed_path.unlink()
    tmp_path.replace(fixed_path)

    atomic_write_text(hist_txt, content)
    write_dataframe(pd.DataFrame(audit_rows), audit_csv)
    return fixed_path, hist_txt, audit_csv


def run() -> tuple[
    Path | None,
    Path | None,
    Path | None,
    int,
    int,
    int,
    dict[str, int],
    dict[str, int],
    dict[str, int],
    int,
    dict[str, int],
]:
    df_forecast = _load_today_forecast()
    if df_forecast.empty:
        logger.warning("Nenhum FORECAST para gerar arquivos do MarketFeeder.")
        return None, None, None, 0, 0, 0, {}, {}, {}, 0, {}

    (
        lines,
        audit_rows,
        skipped_forecast_incomplete,
        counts_by_strategy,
        races_by_strategy,
        exported_category_counts,
        ignored_by_category_total,
        ignored_category_counts,
    ) = _build_lines_and_audit(df_forecast)
    if not lines:
        logger.warning("Nenhuma seleção elegível para exportar ao MarketFeeder.")
        return (
            None,
            None,
            None,
            0,
            skipped_forecast_incomplete,
            0,
            counts_by_strategy,
            races_by_strategy,
            exported_category_counts,
            ignored_by_category_total,
            ignored_category_counts,
        )

    fixed_path, hist_txt, audit_csv = _write_marketfeeder_files(lines, audit_rows)
    logger.info("Arquivo fixo MarketFeeder atualizado: {}", fixed_path)
    logger.info("Histórico diário salvo: {}", hist_txt)
    logger.info("Auditoria salva: {}", audit_csv)
    logger.info("Seleções por strategy_tag: {}", counts_by_strategy)
    logger.info("Distribuição de categorias (exportadas): {}", exported_category_counts)
    logger.info(
        "Corridas ignoradas por categoria não elegível: {} | categorias: {}",
        ignored_by_category_total,
        ignored_category_counts,
    )
    return (
        fixed_path,
        hist_txt,
        audit_csv,
        len(lines),
        skipped_forecast_incomplete,
        len(lines) // 3,
        counts_by_strategy,
        races_by_strategy,
        exported_category_counts,
        ignored_by_category_total,
        ignored_category_counts,
    )


if __name__ == "__main__":
    run()

