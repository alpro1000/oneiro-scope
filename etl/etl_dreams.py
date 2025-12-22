#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL разрешённых источников в формат современного сонника.
- SDDb (Zenodo), Dryad (DOI), figshare/Donders (article IDs), user CSV/JSON.
- Без скрейпа запрещённых сайтов. Magickum НЕ трогаем.
- Генерирует data/dreams_curated.json (масштабируемый список DreamEntry).
"""
import os, re, json, csv, gzip, io, sys, argparse, logging, time
from datetime import datetime, timezone
from urllib.parse import urljoin
import yaml
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from rapidfuzz import process, fuzz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "data", "dreams_curated.json")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
UA = {"User-Agent": "OneiroScope-ETL/1.0 (+https://github.com/alpro1000/oneiro-scope)"}
TIMEOUT = 30
RATE = 0.5  # сек/запрос (бережный режим)

def sleep():
    time.sleep(RATE)

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_symbols(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def safe_get(url):
    sleep()
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return r

def is_texty(name):
    n = name.lower()
    return any(n.endswith(ext) for ext in (".json",".jsonl",".csv",".tsv",".txt"))

def guess_text_field(header_row):
    # ищем колонку с текстом отчёта сна
    candidates = ["text","report","content","dream","transcript","narrative","entry"]
    lower = [h.strip().lower() for h in header_row]
    for c in candidates:
        if c in lower:
            return lower.index(c)
    return None

def normalize_text(s):
    s = re.sub(r'\s+', ' ', (s or '')).strip()
    return s

# ---------- сборщики ----------

def collect_sddb_zenodo(record_id, per_source_max, min_text_len):
    api = f"https://zenodo.org/api/records/{record_id}"
    out = []
    try:
        j = safe_get(api).json()
        files = j.get("files", [])
        for f in files:
            url = f.get("links", {}).get("self")
            name = f.get("key", "")
            if not url or not is_texty(name): 
                continue
            txt = safe_get(url).text
            # JSONL/JSON
            if name.endswith((".json",".jsonl")):
                # пробуем JSONL
                lines = txt.splitlines()
                parsed = False
                for line in lines:
                    try:
                        obj = json.loads(line)
                        t = normalize_text(obj.get("text") or obj.get("report") or "")
                        if len(t) >= min_text_len:
                            out.append({"source":"sddb","url":"https://sleepanddreamdatabase.org/","title":"SDDb item","text":t})
                        parsed = True
                    except json.JSONDecodeError:
                        parsed = False
                        break
                if not parsed:
                    try:
                        data = json.loads(txt)
                        if isinstance(data, list):
                            for obj in data:
                                t = normalize_text(obj.get("text") or obj.get("report") or "")
                                if len(t) >= min_text_len:
                                    out.append({"source":"sddb","url":"https://sleepanddreamdatabase.org/","title":"SDDb item","text":t})
                    except Exception:
                        pass
            # CSV/TSV
            elif name.endswith((".csv",".tsv")):
                delim = "," if name.endswith(".csv") else "\t"
                reader = csv.reader(io.StringIO(txt), delimiter=delim)
                header = next(reader, [])
                idx = guess_text_field(header)
                if idx is None: 
                    continue
                for row in reader:
                    if idx < len(row):
                        t = normalize_text(row[idx])
                        if len(t) >= min_text_len:
                            out.append({"source":"sddb","url":url,"title":"SDDb item","text":t})
            if len(out) >= per_source_max:
                break
    except Exception as e:
        logging.warning(f"SDDb Zenodo error: {e}")
    return out[:per_source_max]

def collect_dryad(doi, per_source_max, min_text_len):
    out = []
    try:
        page = safe_get(f"https://datadryad.org/dataset/doi:{doi}").text
        soup = BeautifulSoup(page, "html.parser")
        links = [a.get("href") for a in soup.select("a[href]")]
        for href in links:
            if not href: continue
            if "download" in href or href.endswith((".csv",".tsv",".json",".zip")):
                try:
                    txt = safe_get(href).text
                except Exception:
                    continue
                # CSV/TSV
                if href.endswith((".csv",".tsv")):
                    delim = "," if href.endswith(".csv") else "\t"
                    reader = csv.reader(io.StringIO(txt), delimiter=delim)
                    header = next(reader, [])
                    idx = guess_text_field(header)
                    if idx is None: 
                        continue
                    for row in reader:
                        if idx < len(row):
                            t = normalize_text(row[idx])
                            if len(t) >= min_text_len:
                                out.append({"source":"dryad","url":href,"title":"Dryad item","text":t})
                # JSON массив
                elif href.endswith(".json"):
                    try:
                        data = json.loads(txt)
                        if isinstance(data, list):
                            for obj in data:
                                t = normalize_text(obj.get("text") or obj.get("report") or "")
                                if len(t) >= min_text_len:
                                    out.append({"source":"dryad","url":href,"title":"Dryad item","text":t})
                    except Exception:
                        pass
            if len(out) >= per_source_max:
                break
    except Exception as e:
        logging.warning(f"Dryad error: {e}")
    return out[:per_source_max]

def collect_figshare(article_id, per_source_max, min_text_len):
    out=[]
    try:
        meta = safe_get(f"https://api.figshare.com/v2/articles/{article_id}").json()
        for f in meta.get("files", []):
            url = f.get("download_url")
            if not url: 
                continue
            try:
                txt = safe_get(url).text
            except Exception:
                continue
            lines = txt.splitlines()
            if not lines: 
                continue
            # пробуем CSV/TSV
            for delim in ("\t", ","):
                reader = csv.reader(io.StringIO(txt), delimiter=delim)
                try:
                    header = next(reader)
                except Exception:
                    header = []
                idx = guess_text_field(header)
                if idx is not None:
                    for row in reader:
                        if idx < len(row):
                            t = normalize_text(row[idx])
                            if len(t) >= min_text_len:
                                out.append({"source":"figshare","url":url,"title":"Figshare item","text":t})
                    break
            # чистый TXT?
            if not out and len(txt) >= min_text_len:
                out.append({"source":"figshare","url":url,"title":"Figshare text","text":normalize_text(txt)})
            if len(out) >= per_source_max:
                break
    except Exception as e:
        logging.warning(f"Figshare error: {e}")
    return out[:per_source_max]

def collect_user_files(paths, per_source_max, min_text_len):
    out=[]
    for p in paths or []:
        try:
            with open(p, "r", encoding="utf-8") as f:
                if p.endswith((".json",".jsonl")):
                    if p.endswith(".jsonl"):
                        for line in f:
                            try:
                                obj = json.loads(line)
                            except Exception:
                                continue
                            t = normalize_text(obj.get("text") or obj.get("report") or obj.get("modern_interpretation") or "")
                            if len(t) >= min_text_len:
                                out.append({"source":"user","url":p,"title":"User file","text":t})
                    else:
                        data = json.load(f)
                        if isinstance(data, list):
                            for obj in data:
                                t = normalize_text(obj.get("text") or obj.get("report") or obj.get("modern_interpretation") or "")
                                if len(t) >= min_text_len:
                                    out.append({"source":"user","url":p,"title":"User file","text":t})
                elif p.endswith((".csv",".tsv")):
                    reader = csv.reader(f, delimiter=("\t" if p.endswith(".tsv") else ","))
                    header = next(reader, [])
                    idx = guess_text_field(header)
                    if idx is None: 
                        continue
                    for row in reader:
                        if idx < len(row):
                            t = normalize_text(row[idx])
                            if len(t) >= min_text_len:
                                out.append({"source":"user","url":p,"title":"User file","text":t})
                else:
                    txt = f.read()
                    if len(txt) >= min_text_len:
                        out.append({"source":"user","url":p,"title":"User file","text":normalize_text(txt)})
        except Exception as e:
            logging.warning(f"User file {p}: {e}")
    return out[:per_source_max]

# ---------- извлечение символов ----------

def lang_of(cfg):
    return cfg.get("lang_default","ru")

def extract_symbols(text, map_for_lang):
    """
    Простая эвристика: ищем леммы/синонимы из словаря.
    Возвращаем список базовых символов по убыванию совпадений.
    """
    t = " " + text.lower() + " "
    counts = {}
    for base, syns in map_for_lang.items():
        hits = 0
        # базовое слово
        if f" {base} " in t:
            hits += 2
        # синонимы
        for s in syns:
            if f" {s} " in t:
                hits += 1
        if hits>0:
            counts[base] = hits
    ordered = sorted(counts.items(), key=lambda x: -x[1])
    return [k for k,_ in ordered[:3]]

def paraphrase(symbol, texts, use_llm=False, model="gpt-4o-mini"):
    joined_preview = " ".join(t[:220] for t in texts[:3])
    if not use_llm:
        # локальный шаблон — нейтральный, оценочный
        hints = "; ".join(set(re.findall(r'\b[А-Яа-яA-Za-z]{5,}\b', " ".join(texts))[:6]))
        out = (f"Оценочно: символ «{symbol}» чаще связан с личным контекстом и эмоциями. "
               f"Смотрите на детали сна и самочувствие после пробуждения. "
               f"Подсказки по контексту: {hints}.")
        return out, 0.8
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        msg = [
          {"role":"system","content":"Ты редактор современного сонника. Пиши кратко, без фатализма; помечай 'оценочно'."},
          {"role":"user","content":f"Составь современную, нейтральную трактовку символа '{symbol}' (2 абзаца + 2 совета). Выдержки: {joined_preview}"}
        ]
        r = client.chat.completions.create(model=model, messages=msg, temperature=0.4)
        return r.choices[0].message.content.strip(), 0.9
    except Exception as e:
        logging.warning(f"LLM error: {e}")
        return f"«{symbol}»: оценочно — важно учитывать контекст и эмоции.", 0.6

def curate(raw, cfg, symbols_map):
    lang = lang_of(cfg)
    map_for_lang = symbols_map.get(lang) or symbols_map.get("ru") or {}
    buckets = {}
    for r in raw:
        syms = extract_symbols(r["text"], map_for_lang)
        for s in syms:
            buckets.setdefault(s, []).append(r)

    curated = []
    use_llm = bool(cfg.get("llm_paraphrase",{}).get("enabled"))
    model = cfg.get("llm_paraphrase",{}).get("model","gpt-4o-mini")

    for symbol, arr in buckets.items():
        sample_texts = [x["text"] for x in arr[:5]]
        interp, conf = paraphrase(symbol, sample_texts, use_llm, model)
        curated.append({
            "symbol": symbol,
            "contexts": [],  # можно добавить ключевые слова/эмоции
            "modern_interpretation": interp,
            "tone": "neutral",
            "lunar_links": [],
            "sources": [{"url": x["url"], "title": x.get("title",""), "date": TODAY, "license":"source-terms"} for x in arr[:5]],
            "confidence": round(conf, 2),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "notes": "Синтез на основе открытых корпусов; оценочно."
        })
    return curated

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT,"etl","sources_config.yml"))
    ap.add_argument("--symbols", default=os.path.join(ROOT,"etl","symbols_map.json"))
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--sources", help="Comma-separated sources to enable (overrides config)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cfg = load_yaml(args.config)

    if args.sources:
        requested = {s.strip() for s in args.sources.split(",") if s.strip()}
        for name in cfg.get("sources", {}):
            cfg["sources"][name]["enabled"] = name in requested
        unknown = sorted(requested - set(cfg.get("sources", {})))
        if unknown:
            logging.warning(f"Неизвестные источники в --sources: {', '.join(unknown)}")
    symbols_map = load_symbols(args.symbols)
    min_len = int(cfg.get("limits",{}).get("min_text_len",100))
    per_max = int(cfg.get("limits",{}).get("per_source_max",5000))

    raw = []

    # SDDb (Zenodo)
    if cfg.get("sources",{}).get("sddb_zenodo",{}).get("enabled"):
        for rid in cfg["sources"]["sddb_zenodo"].get("record_ids",[]):
            logging.info(f"SDDb Zenodo {rid} …")
            raw += collect_sddb_zenodo(rid, per_max, min_len)

    # Dryad
    if cfg.get("sources",{}).get("dryad",{}).get("enabled"):
        for doi in cfg["sources"]["dryad"].get("dois",[]):
            logging.info(f"Dryad {doi} …")
            raw += collect_dryad(doi, per_max, min_len)

    # figshare
    if cfg.get("sources",{}).get("figshare",{}).get("enabled"):
        for aid in cfg["sources"]["figshare"].get("article_ids",[]):
            logging.info(f"figshare {aid} …")
            raw += collect_figshare(aid, per_max, min_len)

    # user files
    if cfg.get("sources",{}).get("user_files",{}).get("enabled"):
        raw += collect_user_files(cfg["sources"]["user_files"].get("paths",[]), per_max, min_len)

    if not raw:
        logging.error("Нет сырых данных. Убедитесь, что источники включены и доступны.")
        sys.exit(2)

    logging.info(f"RAW получено: {len(raw)}")
    curated = curate(raw, cfg, symbols_map)
    logging.info(f"Символов сформировано: {len(curated)}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(curated, f, ensure_ascii=False, indent=2)
    logging.info(f"OK → {args.out}")

if __name__ == "__main__":
    main()

