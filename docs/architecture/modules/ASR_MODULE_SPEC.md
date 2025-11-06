# ASR Module — Техническая спецификация

## 1. Обзор

ASR (Automatic Speech Recognition) модуль обеспечивает транскрипцию голосовых записей снов в текст для последующего анализа.

---

## 2. Требования

### 2.1 Функциональные требования

| ID | Требование | Приоритет |
|----|------------|-----------|
| ASR-F-001 | Поддержка RU/EN языков | P0 |
| ASR-F-002 | Автоматическое определение языка | P0 |
| ASR-F-003 | Confidence score ≥ 0.90 | P0 |
| ASR-F-004 | Fallback на Telegram при низком confidence | P1 |
| ASR-F-005 | Макс. длительность записи: 3 минуты | P0 |
| ASR-F-006 | Поддержка форматов: WebM, Ogg, MP3, M4A | P0 |
| ASR-F-007 | Timestamp-based сегментация | P2 |

### 2.2 Нефункциональные требования

| ID | Метрика | Значение |
|----|---------|----------|
| ASR-NF-001 | Latency (p95) | ≤ 5s для 1 мин записи |
| ASR-NF-002 | WER (Word Error Rate) | ≤ 10% для RU/EN |
| ASR-NF-003 | Throughput | 100 concurrent requests |
| ASR-NF-004 | Uptime | 99.5% |
| ASR-NF-005 | Storage retention | 24 часа (auto-delete) |

---

## 3. Архитектура

### 3.1 System Context

```
┌─────────────┐
│   Client    │
│ (Web/Mobile)│
└──────┬──────┘
       │ Audio Upload
       ▼
┌─────────────────────────────────────┐
│        ASR Service (FastAPI)        │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Audio Ingestion & Validation│  │
│  └────────────┬─────────────────┘  │
│               ▼                     │
│  ┌──────────────────────────────┐  │
│  │   Primary: Whisper API       │  │
│  │   Fallback: Vosk (offline)   │  │
│  └────────────┬─────────────────┘  │
│               ▼                     │
│  ┌──────────────────────────────┐  │
│  │  Post-processing & Validation│  │
│  └────────────┬─────────────────┘  │
└───────────────┼─────────────────────┘
                ▼
       ┌──────────────┐
       │   Response   │
       │ (JSON + conf)│
       └──────────────┘
```

### 3.2 Component Diagram

```
backend/
├── services/
│   └── asr/
│       ├── __init__.py
│       ├── service.py          # Main ASR orchestration
│       ├── whisper_client.py   # OpenAI Whisper wrapper
│       ├── vosk_client.py      # Offline fallback
│       ├── audio_processor.py  # Format conversion, validation
│       ├── language_detector.py# Language detection
│       └── schemas.py          # Pydantic models
├── api/
│   └── v1/
│       └── asr.py              # FastAPI endpoints
└── tasks/
    └── asr_tasks.py            # Celery background tasks
```

---

## 4. API Specification

### 4.1 Endpoints

#### POST /api/v1/asr/transcribe

**Description**: Транскрибирует аудио файл в текст

**Request**:
```http
POST /api/v1/asr/transcribe
Content-Type: multipart/form-data

{
  "audio": <file>,
  "language": "auto|ru|en",  // optional
  "model": "whisper-large-v3",  // optional
  "prompt": "context hint"   // optional
}
```

**Response** (Success):
```json
{
  "transcript": "Мне приснилось, что я летаю над городом...",
  "confidence": 0.94,
  "language": "ru",
  "duration_seconds": 45.3,
  "model_used": "whisper-large-v3",
  "segments": [
    {
      "start": 0.0,
      "end": 12.5,
      "text": "Мне приснилось, что я летаю над городом",
      "confidence": 0.95
    }
  ],
  "metadata": {
    "audio_format": "webm",
    "sample_rate": 16000,
    "processing_time_ms": 1234
  }
}
```

**Response** (Low Confidence):
```json
{
  "transcript": "unclear audio...",
  "confidence": 0.72,
  "fallback_required": true,
  "fallback_method": "telegram",
  "error_code": "LOW_CONFIDENCE",
  "suggestion": "Please try recording in a quieter environment"
}
```

**Error Responses**:
```json
// File too large
{
  "error": "FILE_TOO_LARGE",
  "message": "Audio duration exceeds 180 seconds",
  "max_duration_seconds": 180
}

// Unsupported format
{
  "error": "UNSUPPORTED_FORMAT",
  "message": "Format .wav not supported",
  "supported_formats": ["webm", "ogg", "mp3", "m4a"]
}

// Processing failed
{
  "error": "PROCESSING_FAILED",
  "message": "Transcription service unavailable",
  "retry_after_seconds": 30
}
```

#### GET /api/v1/asr/status/{task_id}

**Description**: Проверить статус асинхронной транскрипции

**Response**:
```json
{
  "task_id": "uuid",
  "status": "pending|processing|completed|failed",
  "progress": 0.65,
  "result": { /* transcript object if completed */ },
  "error": "error message if failed"
}
```

---

## 5. Implementation Details

### 5.1 Audio Processing Pipeline

```python
# backend/services/asr/audio_processor.py

from pydub import AudioSegment
import tempfile
from pathlib import Path

class AudioProcessor:
    SUPPORTED_FORMATS = ["webm", "ogg", "mp3", "m4a"]
    TARGET_SAMPLE_RATE = 16000  # Hz
    TARGET_CHANNELS = 1  # Mono
    MAX_DURATION = 180  # seconds

    def validate_audio(self, file_path: Path) -> dict:
        """Validate audio file constraints"""
        audio = AudioSegment.from_file(file_path)

        duration = len(audio) / 1000  # milliseconds to seconds
        if duration > self.MAX_DURATION:
            raise ValueError(f"Duration {duration}s exceeds max {self.MAX_DURATION}s")

        return {
            "duration": duration,
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "format": file_path.suffix.lstrip('.')
        }

    def convert_to_wav(self, input_path: Path) -> Path:
        """Convert to WAV 16kHz mono for Whisper"""
        audio = AudioSegment.from_file(input_path)

        # Convert to mono
        if audio.channels > 1:
            audio = audio.set_channels(1)

        # Resample to 16kHz
        if audio.frame_rate != self.TARGET_SAMPLE_RATE:
            audio = audio.set_frame_rate(self.TARGET_SAMPLE_RATE)

        # Export as WAV
        output_path = Path(tempfile.mktemp(suffix=".wav"))
        audio.export(output_path, format="wav")

        return output_path
```

### 5.2 Whisper Integration

```python
# backend/services/asr/whisper_client.py

import openai
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class WhisperClient:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "whisper-1"  # OpenAI hosted model

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> dict:
        """Transcribe audio using OpenAI Whisper API"""

        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    prompt=prompt,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )

            # Extract confidence from segments
            avg_confidence = self._calculate_confidence(response)

            return {
                "transcript": response.text,
                "language": response.language,
                "duration": response.duration,
                "confidence": avg_confidence,
                "segments": [
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                        "confidence": getattr(seg, 'avg_logprob', None)
                    }
                    for seg in response.segments
                ]
            }

        except openai.APIError as e:
            logger.error(f"Whisper API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    def _calculate_confidence(self, response) -> float:
        """Calculate average confidence from segments"""
        if not response.segments:
            return 0.5

        # Convert log probability to confidence (0-1)
        # avg_logprob ranges from -inf to 0
        confidences = []
        for seg in response.segments:
            if hasattr(seg, 'avg_logprob') and seg.avg_logprob is not None:
                # Map logprob to confidence: exp(logprob)
                conf = min(1.0, max(0.0, 1.0 + seg.avg_logprob / 5))
                confidences.append(conf)

        return sum(confidences) / len(confidences) if confidences else 0.5
```

### 5.3 Vosk Fallback (Offline)

```python
# backend/services/asr/vosk_client.py

from vosk import Model, KaldiRecognizer
import wave
import json
import logging

logger = logging.getLogger(__name__)

class VoskClient:
    def __init__(self, model_path: str = "/models/vosk-model-ru-0.42"):
        self.model = Model(model_path)

    def transcribe(self, audio_path: Path) -> dict:
        """Offline transcription using Vosk"""

        wf = wave.open(str(audio_path), "rb")

        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() not in [8000, 16000]:
            raise ValueError("Audio must be mono WAV 16kHz")

        rec = KaldiRecognizer(self.model, wf.getframerate())
        rec.SetWords(True)

        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                results.append(result)

        final_result = json.loads(rec.FinalResult())
        results.append(final_result)

        transcript = " ".join(r.get("text", "") for r in results)

        # Vosk confidence is estimated
        avg_confidence = self._estimate_confidence(results)

        return {
            "transcript": transcript,
            "confidence": avg_confidence,
            "language": "ru",  # Model-dependent
            "model_used": "vosk-offline"
        }

    def _estimate_confidence(self, results: list) -> float:
        """Estimate confidence from word-level results"""
        all_words = []
        for r in results:
            if "result" in r:
                all_words.extend(r["result"])

        if not all_words:
            return 0.5

        confidences = [w.get("conf", 0.5) for w in all_words]
        return sum(confidences) / len(confidences)
```

### 5.4 Service Orchestration

```python
# backend/services/asr/service.py

from typing import Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ASRService:
    CONFIDENCE_THRESHOLD = 0.90

    def __init__(
        self,
        whisper_client: WhisperClient,
        vosk_client: VoskClient,
        audio_processor: AudioProcessor
    ):
        self.whisper = whisper_client
        self.vosk = vosk_client
        self.processor = audio_processor

    async def transcribe(
        self,
        audio_file: Path,
        language: Optional[str] = None,
        use_fallback: bool = True
    ) -> dict:
        """Main transcription method with fallback logic"""

        # Step 1: Validate audio
        try:
            metadata = self.processor.validate_audio(audio_file)
        except ValueError as e:
            logger.error(f"Audio validation failed: {e}")
            return {
                "error": "VALIDATION_FAILED",
                "message": str(e)
            }

        # Step 2: Convert to WAV if needed
        wav_file = self.processor.convert_to_wav(audio_file)

        # Step 3: Try Whisper (primary)
        try:
            result = await self.whisper.transcribe(
                wav_file,
                language=language
            )

            # Check confidence threshold
            if result["confidence"] >= self.CONFIDENCE_THRESHOLD:
                result["metadata"] = metadata
                return result

            logger.warning(
                f"Low confidence {result['confidence']:.2f}, "
                f"threshold {self.CONFIDENCE_THRESHOLD}"
            )

            # If fallback disabled, return low-confidence result
            if not use_fallback:
                result["fallback_required"] = True
                result["fallback_method"] = "telegram"
                return result

        except Exception as e:
            logger.error(f"Whisper failed: {e}")
            if not use_fallback:
                raise

        # Step 4: Fallback to Vosk
        if use_fallback:
            try:
                logger.info("Attempting Vosk fallback")
                result = self.vosk.transcribe(wav_file)
                result["fallback_used"] = True
                result["metadata"] = metadata
                return result
            except Exception as e:
                logger.error(f"Vosk fallback failed: {e}")
                raise

        # Both failed
        return {
            "error": "TRANSCRIPTION_FAILED",
            "message": "All transcription methods failed",
            "fallback_method": "telegram"
        }
```

---

## 6. Quality Gates

### 6.1 Test Coverage

| Component | Target Coverage | Type |
|-----------|----------------|------|
| AudioProcessor | 90% | Unit |
| WhisperClient | 85% | Integration |
| VoskClient | 85% | Integration |
| ASRService | 90% | Unit + Integration |
| API Endpoints | 95% | E2E |

### 6.2 Performance Benchmarks

```python
# tests/performance/test_asr_performance.py

import pytest
from pathlib import Path

@pytest.mark.performance
async def test_transcription_latency():
    """P95 latency must be <= 5s for 1min audio"""

    audio_file = Path("fixtures/1min_ru.webm")

    latencies = []
    for _ in range(100):
        start = time.time()
        result = await asr_service.transcribe(audio_file)
        latencies.append(time.time() - start)

    p95 = np.percentile(latencies, 95)
    assert p95 <= 5.0, f"P95 latency {p95:.2f}s exceeds 5s"

@pytest.mark.performance
async def test_concurrent_requests():
    """Must handle 100 concurrent requests"""

    tasks = [
        asr_service.transcribe(audio_file)
        for _ in range(100)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if not isinstance(r, Exception))
    assert success_count >= 95, "Less than 95% success rate"
```

### 6.3 Quality Metrics

```yaml
# Monitoring thresholds
metrics:
  word_error_rate:
    ru: <= 0.10
    en: <= 0.08

  confidence_distribution:
    p50: >= 0.92
    p95: >= 0.85

  api_latency:
    p50: <= 2s
    p95: <= 5s
    p99: <= 10s

  error_rates:
    whisper_api_errors: <= 0.01
    fallback_trigger_rate: <= 0.05
    total_failures: <= 0.001
```

---

## 7. Deployment

### 7.1 Docker Configuration

```dockerfile
# backend/services/asr/Dockerfile

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Download Vosk model
RUN mkdir -p /models && \
    cd /models && \
    wget https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip && \
    unzip vosk-model-ru-0.42.zip && \
    rm vosk-model-ru-0.42.zip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 7.2 Environment Variables

```bash
# .env.asr

# OpenAI Whisper
OPENAI_API_KEY=sk-...
WHISPER_MODEL=whisper-1

# Vosk
VOSK_MODEL_PATH=/models/vosk-model-ru-0.42

# Processing
ASR_MAX_DURATION=180
ASR_CONFIDENCE_THRESHOLD=0.90
ASR_STORAGE_TTL=86400  # 24 hours

# Performance
ASR_MAX_WORKERS=4
ASR_QUEUE_SIZE=100

# Monitoring
SENTRY_DSN=https://...
```

---

## 8. Monitoring & Observability

### 8.1 Metrics

```python
# backend/services/asr/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Request metrics
asr_requests_total = Counter(
    'asr_requests_total',
    'Total ASR requests',
    ['language', 'model', 'status']
)

asr_processing_duration = Histogram(
    'asr_processing_duration_seconds',
    'ASR processing duration',
    ['model'],
    buckets=[1, 2, 5, 10, 30]
)

# Quality metrics
asr_confidence_score = Histogram(
    'asr_confidence_score',
    'Confidence score distribution',
    ['language', 'model'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
)

# Fallback metrics
asr_fallback_triggered = Counter(
    'asr_fallback_triggered_total',
    'Number of fallback triggers',
    ['reason']
)

# Active processing
asr_active_tasks = Gauge(
    'asr_active_tasks',
    'Number of active ASR tasks'
)
```

### 8.2 Logging

```python
# Structured logging format
{
  "timestamp": "2025-11-01T12:34:56Z",
  "level": "INFO",
  "service": "asr",
  "event": "transcription_completed",
  "task_id": "uuid",
  "duration_ms": 1234,
  "audio_duration_s": 45.3,
  "language": "ru",
  "model": "whisper-large-v3",
  "confidence": 0.94,
  "fallback_used": false,
  "user_id": "uuid",
  "trace_id": "uuid"
}
```

---

## 9. Error Handling

### 9.1 Error Codes

| Code | Description | HTTP Status | Recovery |
|------|-------------|-------------|----------|
| FILE_TOO_LARGE | Audio exceeds 3 minutes | 400 | Split recording |
| UNSUPPORTED_FORMAT | Format not supported | 400 | Convert file |
| LOW_CONFIDENCE | Confidence < 0.90 | 200 | Use Telegram fallback |
| PROCESSING_FAILED | Transcription failed | 500 | Retry with backoff |
| RATE_LIMIT_EXCEEDED | Too many requests | 429 | Wait and retry |
| SERVICE_UNAVAILABLE | Backend unavailable | 503 | Retry after delay |

### 9.2 Retry Strategy

```python
# backend/services/asr/retry.py

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((openai.APIError, TimeoutError))
)
async def transcribe_with_retry(client, audio_path):
    return await client.transcribe(audio_path)
```

---

## 10. Security

### 10.1 File Validation

```python
ALLOWED_EXTENSIONS = {"webm", "ogg", "mp3", "m4a"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

def validate_upload(file):
    # Check extension
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension .{ext} not allowed")

    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset

    if size > MAX_FILE_SIZE:
        raise ValueError(f"File size {size} exceeds {MAX_FILE_SIZE}")

    # Check magic bytes (file signature)
    header = file.read(12)
    file.seek(0)

    if not is_valid_audio_header(header):
        raise ValueError("Invalid audio file signature")
```

### 10.2 Data Privacy

- Audio files stored temporarily (24h auto-delete)
- No PII extraction from audio
- GDPR-compliant: user can request deletion
- End-to-end encryption for Telegram uploads

---

## 11. Cost Optimization

### 11.1 Pricing (OpenAI Whisper)

```
- $0.006 per minute
- Average dream narration: 2 minutes
- Cost per transcription: ~$0.012

Monthly estimates:
- 1,000 users × 2 dreams/month = 2,000 transcriptions
- Cost: 2,000 × $0.012 = $24/month
```

### 11.2 Optimizations

1. **Caching**: Cache transcripts for identical audio (hash-based)
2. **Compression**: Use Opus codec (50% smaller than MP3)
3. **Vosk first**: For free-tier users, try Vosk before Whisper
4. **Batch processing**: Group requests to reduce API calls

---

## 12. Testing Strategy

### 12.1 Test Fixtures

```
tests/fixtures/audio/
├── clean_speech_ru_30s.webm       # High quality
├── noisy_speech_ru_60s.mp3        # Background noise
├── quiet_speech_en_45s.ogg        # Low volume
├── multilingual_mix_90s.m4a       # Code-switching
└── invalid_corrupted.webm         # Corrupted file
```

### 12.2 Test Cases

```python
# tests/unit/test_asr_service.py

@pytest.mark.asyncio
async def test_high_quality_audio():
    """Clean audio should have confidence >= 0.95"""
    result = await asr_service.transcribe("fixtures/clean_speech_ru_30s.webm")
    assert result["confidence"] >= 0.95
    assert result["language"] == "ru"

@pytest.mark.asyncio
async def test_noisy_audio_triggers_fallback():
    """Noisy audio should trigger fallback"""
    result = await asr_service.transcribe("fixtures/noisy_speech_ru_60s.mp3")
    assert result["confidence"] < 0.90 or result.get("fallback_used") == True

@pytest.mark.asyncio
async def test_corrupted_file_handling():
    """Corrupted file should return validation error"""
    with pytest.raises(ValueError, match="Invalid audio"):
        await asr_service.transcribe("fixtures/invalid_corrupted.webm")

@pytest.mark.asyncio
async def test_language_detection():
    """Service should auto-detect language"""
    result = await asr_service.transcribe("fixtures/clean_speech_ru_30s.webm", language=None)
    assert result["language"] in ["ru", "en"]
```

---

## 13. Future Enhancements

### Phase 2 (Weeks 9-12)
- [ ] Real-time streaming transcription
- [ ] Speaker diarization (multi-speaker dreams)
- [ ] Emotion detection from voice
- [ ] Custom vocabulary (dream-specific terms)

### Phase 3 (Months 4-6)
- [ ] Self-hosted Whisper large-v3 (cost optimization)
- [ ] Fine-tuned model on dream narrations
- [ ] Support for 10+ languages
- [ ] Voice activity detection (VAD) for silence removal

---

**Document Version**: 1.0
**Last Updated**: 2025-11-01
**Owner**: ASR Module Team
**Reviewers**: Architecture Team, Backend Team
