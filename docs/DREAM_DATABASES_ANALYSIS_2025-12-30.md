# Dream Databases Analysis & Integration Strategy

**Date:** 2025-12-30
**Status:** Analysis Complete
**Branch:** `claude/update-documentation-En0hK`

---

## 📊 Executive Summary

Analyzed 4 dream database sources for potential integration:

1. ✅ **DreamBank** - Already integrated via `DreamBankConnector`
2. ✅ **DREAMS Polysomnography** - Already has connector (EDF files)
3. ❌ **dreamento** - NOT relevant (sleep scoring tool, not dream content)
4. 🟡 **dreambank (krank)** - Enhanced DreamBank parser (potential upgrade)

**Recommendation:** Current integration is sufficient. Consider upgrading DreamBank connector to use krank's structured format.

---

## 🗂️ Database Comparison Table

| Database | Type | Already Connected? | Data Format | Size | Access Method | Recommendation |
|----------|------|-------------------|-------------|------|---------------|----------------|
| **DreamBank.net** | Dream narratives | ✅ Yes | CSV/TSV | ~20,000 dreams | API/scraping | ✅ Keep current |
| **DREAMS (Zenodo)** | Polysomnography (EDF) | ✅ Yes | EDF files | 8 datasets | Direct download | ✅ Keep current |
| **dreambank (krank)** | Structured DreamBank | 🟡 Partial | CSV (curated) | Same as DreamBank | GitHub/Zenodo | 🔄 Consider upgrade |
| **dreamento** | Sleep scoring tool | ❌ No | Python scripts | N/A | N/A | ❌ Not relevant |

---

## 📁 Detailed Source Analysis

### 1. DreamBank.net ✅ Already Integrated

**Repository:** https://dreambank.net
**Our Integration:** `backend/services/dreams/dreambank_loader.py`

**What it is:**
- Research repository of dream narratives
- ~20,000+ dreams from various series (individuals, research studies)
- Hall/Van de Castle normative data (1966 study)

**Current Integration:**
```python
# backend/services/dreams/dreambank_loader.py:51-80
class DreamBankLoader:
    """Loads Hall/Van de Castle normative data."""

    def __init__(self):
        self.norms = {}  # HVDC norms from backend/services/dreams/knowledge_base/hvdc_norms.json
        self.indicators = {}
        self.thresholds = {}
```

**Connector:**
```python
# backend/services/dreams/data_sources/connectors.py:91-117
class DreamBankConnector(BaseConnector):
    dataset = "DreamBank"

    def load(self) -> List[DreamSourceRecord]:
        table = self._read_table()  # Reads CSV/TSV/JSON
        # Returns DreamSourceRecord with dream_text + metadata
```

**Data Format:**
- CSV/TSV files with columns: `dream_text`, `series`, `gender`, `age`, `date`, `locale`
- JSON for HVDC norms

**Status:** ✅ **FULLY INTEGRATED**

---

### 2. DREAMS Polysomnography Database ✅ Already Integrated

**Repository:** https://zenodo.org/records/2650142
**Our Integration:** `backend/services/dreams/data_sources/connectors.py:120-140`

**What it is:**
- 8 polysomnography (PSG) databases from sleep lab
- EEG/EOG/EMG recordings in European Data Format (EDF)
- Expert annotations for:
  - Sleep stages (20 subjects, 27 patients)
  - Artifacts
  - Sleep spindles
  - K-complexes
  - REMs (rapid eye movements)
  - PLMs (periodic limb movements)
  - Apnea events

**Databases:**
1. DREAMS Subjects Database (20 recordings)
2. DREAMS Patients Database (27 recordings)
3. DREAMS Artifacts Database (20 excerpts)
4. DREAMS Sleep Spindles Database (8 excerpts)
5. DREAMS K-complexes Database (5 excerpts)
6. DREAMS REMs Database (9 excerpts)
7. DREAMS PLMs Database (10 recordings)
8. DREAMS Apnea Database (12 recordings)

**Current Integration:**
```python
# backend/services/dreams/data_sources/connectors.py:120-140
class DREAMSConnector(BaseConnector):
    dataset = "DREAMS"

    def load_edf(self, sleep_stage: Optional[str] = None, participant_id: Optional[str] = None) -> List[PhysiologicalEvent]:
        raw = mne.io.read_raw_edf(self.path_info.uri, preload=False)
        # Returns PhysiologicalEvent with channel info, sampling rate, duration
```

**Data Format:**
- EDF files (European Data Format)
- Readable via MNE-Python library (already in dependencies)

**Status:** ✅ **CONNECTOR EXISTS** (needs EDF files downloaded)

**Storage Strategy:**
- ❌ **Do NOT store locally** - EDF files are LARGE (~100MB+ per recording)
- ✅ **On-demand download** - Download specific files when needed for research
- ✅ **Metadata cache** - Store metadata (participant IDs, sleep stages, file URLs) in database

---

### 3. dreambank (krank) 🟡 Enhanced Parser

**Repository:** https://github.com/krank-sources/dreambank.git
**Purpose:** Structured parsing of DreamBank.net HTML into CSV

**What it is:**
- Curated version of DreamBank.net
- Parses HTML from dreambank.net → CSV format
- Multiple corpora (HVDC, UCSC 1996, Urbina 1975)
- Provides krank-ready datasets

**Repository Structure:**
```
dreambank/
├── raw/
│   ├── prepare.ipynb         # Downloads HTML from dreambank.net
│   └── registry.json         # MD5 hashes of HTML files
├── prepare.ipynb             # Parses HTML → datasets.csv + dreams.csv
├── hvdc/                     # Hall/Van de Castle corpus
├── ucsc1996/                 # UCSC 1996 study
└── urbina1975/               # Urbina 1975 study
```

**Key Finding:**
This repo **does NOT contain dream data files** - only parsing notebooks. The actual datasets are:
- Published on Zenodo (https://zenodo.org/communities/krank)
- Generated by running the notebooks

**Advantages over current integration:**
1. ✅ Structured CSV format (easier to parse)
2. ✅ Curated datasets (already cleaned)
3. ✅ Multiple corpora (HVDC, UCSC, Urbina)
4. ✅ Provenance tracking (MD5 hashes)

**Recommendation:**
🔄 **UPGRADE OPTION** - Replace current DreamBankConnector with krank's CSV format

**Implementation:**
```python
# Option 1: Download curated CSVs from Zenodo
# Option 2: Run krank's parsing notebooks locally
# Option 3: Hybrid - use krank's parser, store CSVs locally
```

**Storage Strategy:**
- ✅ **Store locally** - CSV files are small (~5-20MB total)
- ✅ **Version control** - Track krank release versions
- ✅ **Periodic updates** - Check for new releases quarterly

---

### 4. dreamento ❌ NOT RELEVANT

**Repository:** https://github.com/dreamento/dreamento.git
**Purpose:** Sleep EEG analysis tool

**What it is:**
- Python GUI for real-time and offline sleep data analysis
- Automatic sleep staging (autoscoring)
- Event detection (spindles, K-complexes, REMs)
- ZMax headband integration
- **NOT a dream content database**

**Why NOT relevant:**
- ❌ No dream narratives
- ❌ No dream content analysis
- ❌ Only polysomnography analysis tool
- ❌ Requires ZMax hardware

**Verdict:** ❌ **DO NOT INTEGRATE**

---

## 🛠️ Integration Recommendations

### Immediate Actions (P1)

#### ✅ Keep Current Integrations
No changes needed for:
- `DreamBankConnector` - Works with CSV/TSV/JSON
- `DREAMSConnector` - Works with EDF files
- `DreamBankLoader` - HVDC norms already integrated

### Short-term Enhancements (P2)

#### 🔄 Consider krank Upgrade

**Option A: Use krank's curated datasets**

1. Download CSVs from Zenodo:
   ```bash
   # HVDC corpus
   wget https://zenodo.org/record/[krank-hvdc]/files/hvdc.csv

   # UCSC 1996
   wget https://zenodo.org/record/[krank-ucsc]/files/ucsc1996.csv

   # Urbina 1975
   wget https://zenodo.org/record/[krank-urbina]/files/urbina1975.csv
   ```

2. Store in `backend/data/dream_corpora/`:
   ```
   backend/data/dream_corpora/
   ├── hvdc.csv
   ├── ucsc1996.csv
   └── urbina1975.csv
   ```

3. Update `DreamBankConnector`:
   ```python
   class DreamBankConnector(BaseConnector):
       dataset = "DreamBank"

       def __init__(self, corpus: str = "hvdc"):
           """
           Args:
               corpus: "hvdc", "ucsc1996", or "urbina1975"
           """
           data_dir = Path(__file__).parent.parent / "data" / "dream_corpora"
           path = data_dir / f"{corpus}.csv"
           super().__init__(path)
           self.corpus = corpus
   ```

**Option B: Run krank's parser locally**

1. Clone krank repo
2. Run `prepare.ipynb` to download HTML
3. Parse to CSV
4. Store CSVs in our repo

**Recommendation:** **Option A** (use pre-curated datasets from Zenodo)

**Benefits:**
- ✅ Cleaner data (already curated)
- ✅ Versioned releases
- ✅ Smaller download size
- ✅ No HTML parsing needed

**Effort:** ~2 hours
- Download CSVs
- Update connector
- Test loading
- Update documentation

---

### Long-term Enhancements (P3)

#### 1. DREAMS EDF Integration

**Current State:** Connector exists, no files stored

**Action Plan:**
1. Download metadata for all 8 DREAMS databases
2. Store metadata in PostgreSQL:
   ```sql
   CREATE TABLE dreams_edf_files (
       id SERIAL PRIMARY KEY,
       database VARCHAR(50),  -- "subjects", "patients", "spindles", etc.
       participant_id VARCHAR(20),
       sleep_stage VARCHAR(20),
       file_url TEXT,
       file_size_mb FLOAT,
       duration_seconds INT,
       channels JSONB,
       sampling_rate FLOAT,
       downloaded BOOLEAN DEFAULT FALSE,
       local_path TEXT
   );
   ```

3. On-demand download:
   ```python
   async def download_edf_if_needed(file_id: int):
       file = db.query(DreamsEdfFile).get(file_id)
       if not file.downloaded:
           await download_from_zenodo(file.file_url, file.local_path)
           file.downloaded = True
   ```

**Benefits:**
- Correlate dream content with sleep stages
- Analyze REM vs NREM dreams
- Research validation

**Effort:** ~1 week
- Download metadata
- Create database schema
- Implement download logic
- Test with sample files

#### 2. Expand Symbol Knowledge Base

**Current:** 56 symbols in `backend/services/dreams/knowledge_base/symbols.json`

**Enhancement:** Extract symbols from DreamBank corpora

```python
def extract_common_symbols(corpus_path: str, min_frequency: int = 100):
    """Extract frequently occurring symbols from dream corpus."""
    connector = DreamBankConnector(corpus_path)
    dreams = connector.load()

    # Tokenize, count, filter
    symbol_counts = Counter()
    for dream in dreams:
        tokens = tokenize(dream.dream_text)
        symbol_counts.update(tokens)

    # Return symbols with frequency > min_frequency
    return [sym for sym, count in symbol_counts.items() if count >= min_frequency]
```

**Effort:** ~3 days

---

## 📊 Summary Table: Current vs Proposed

| Component | Current State | Proposed Enhancement | Priority | Effort |
|-----------|--------------|---------------------|----------|--------|
| **DreamBank narratives** | ✅ CSV connector | 🔄 Upgrade to krank curated CSVs | P2 | 2 hours |
| **HVDC norms** | ✅ JSON file loaded | ✅ Keep as-is | - | - |
| **DREAMS EDF files** | ✅ Connector exists | 📥 Add metadata DB + on-demand download | P3 | 1 week |
| **Symbols knowledge base** | ✅ 56 symbols | 📈 Extract from corpus (auto-generate) | P3 | 3 days |
| **dreamento** | ❌ Not integrated | ❌ Do not integrate | - | - |

---

## 🔧 Parsing Strategies

### DreamBank (krank CSV format)

**Input:** CSV file from Zenodo
**Columns:** `dream_id`, `series`, `dream_text`, `gender`, `age`, `date`, `locale`

**Parser:**
```python
def parse_krank_csv(csv_path: str) -> List[DreamSourceRecord]:
    df = pd.read_csv(csv_path)
    records = []

    for _, row in df.iterrows():
        metadata = DreamSourceMetadata(
            dataset="DreamBank",
            source=row.get("series"),
            gender=row.get("gender"),
            age=row.get("age"),
            date=row.get("date"),
            locale=row.get("locale") or "en"
        )
        records.append(DreamSourceRecord(
            dream_text=row["dream_text"],
            metadata=metadata,
            provenance=build_provenance("krank", len(df))
        ))

    return records
```

**Storage:** Store CSV files in `backend/data/dream_corpora/`

---

### DREAMS EDF Files

**Input:** EDF file from Zenodo
**Format:** European Data Format (binary)

**Parser:** Already implemented via `DREAMSConnector.load_edf()`

```python
def parse_edf(file_path: str) -> PhysiologicalEvent:
    raw = mne.io.read_raw_edf(file_path, preload=False)

    return PhysiologicalEvent(
        participant_id=extract_from_filename(file_path),
        sleep_stage=detect_stage(raw),
        channel_names=raw.ch_names,
        sampling_rate=raw.info['sfreq'],
        start_time=raw.info['meas_date'],
        duration_seconds=raw.n_times / raw.info['sfreq']
    )
```

**Storage:**
- ❌ Do NOT store EDF files (~100MB+ each)
- ✅ Store metadata only
- ✅ Download on-demand for research

---

## 💾 Storage vs API Approach

### DreamBank Narratives

**Decision:** ✅ **STORE LOCALLY** (CSV files)

**Reasons:**
- Small size (~5-20MB total)
- Offline access for users
- Fast queries
- No API rate limits
- Data stability (historical corpus)

**Implementation:**
```
backend/data/dream_corpora/
├── hvdc.csv              # ~3MB
├── ucsc1996.csv          # ~2MB
├── urbina1975.csv        # ~1MB
└── metadata.json         # Provenance tracking
```

---

### DREAMS Polysomnography (EDF)

**Decision:** 🌐 **METADATA STORED, FILES ON-DEMAND**

**Reasons:**
- Large files (~100MB+ per recording, ~10GB total)
- Rarely accessed (only for research validation)
- Zenodo provides stable URLs
- Expensive to store in production

**Implementation:**
```sql
-- Store metadata only
CREATE TABLE dreams_edf_metadata (
    id SERIAL PRIMARY KEY,
    database VARCHAR(50),
    zenodo_url TEXT,
    file_size_mb FLOAT,
    participant_id VARCHAR(20),
    sleep_stage VARCHAR(20),
    cached_locally BOOLEAN DEFAULT FALSE,
    cache_path TEXT
);
```

**On-demand download:**
```python
async def get_edf_data(file_id: int):
    metadata = db.query(DreamsEdfMetadata).get(file_id)

    # Check cache
    if metadata.cached_locally and Path(metadata.cache_path).exists():
        return load_edf(metadata.cache_path)

    # Download temporarily
    tmp_path = f"/tmp/dreams_edf_{file_id}.edf"
    await download_from_zenodo(metadata.zenodo_url, tmp_path)

    # Load and return (delete after use or cache for 24h)
    return load_edf(tmp_path)
```

---

## ✅ Action Items

### P1 - Immediate (Keep Current)
- [x] DreamBank connector working
- [x] HVDC norms loaded
- [x] DREAMS connector code exists
- [x] Documentation written

### P2 - Short-term (2-3 days)
- [ ] Download krank curated CSVs from Zenodo
- [ ] Store CSVs in `backend/data/dream_corpora/`
- [ ] Test DreamBankConnector with new format
- [ ] Update CLAUDE.md with new data sources

### P3 - Long-term (1-2 weeks)
- [ ] Create `dreams_edf_metadata` table
- [ ] Download DREAMS metadata from Zenodo
- [ ] Implement on-demand EDF download
- [ ] Auto-extract symbols from corpus
- [ ] Add corpus selection to API (`GET /api/v1/dreams/corpora`)

---

## 📚 References

- **DreamBank.net:** https://dreambank.net
- **Hall & Van de Castle (1966):** The Content Analysis of Dreams
- **Domhoff & Schneider (2008):** doi:10.1016/j.concog.2008.06.010
- **DREAMS Database:** https://zenodo.org/records/2650142
- **krank (dreambank parser):** https://github.com/krank-sources/dreambank
- **krank Zenodo:** https://zenodo.org/communities/krank

---

**Status:** ✅ Analysis complete, current integration sufficient
**Next:** Consider krank upgrade (P2, ~2 hours effort)
**Commit:** Pending documentation commit
