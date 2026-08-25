<p align="center">
  <img src="../assets/bindu_logo.png" alt="Bindu" width="120" />
</p>

<h1 align="center">Bindu</h1>

<p align="center">
    <a href="https://www.python.org/downloads/"><img alt="Python Version" src="https://img.shields.io/badge/python-3.12+-blue.svg"></a>
    <a href="https://pypi.org/project/bindu/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/bindu.svg"></a>
    <a href="https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18"><img alt="Coverage" src="https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18"></a>
    <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img alt="Tests" src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg"></a>
    <a href="https://discord.gg/3w5zuYUuwt"><img alt="Discord" src="https://img.shields.io/badge/Discord-7289DA?logo=discord&logoColor=white"></a>
    <a href="https://github.com/getbindu/Bindu/graphs/contributors"><img alt="Contributors" src="https://img.shields.io/github/contributors/getbindu/Bindu"></a>
    <a href="https://hits.sh/github.com/Saptha-me/Bindu.svg"><img alt="Hits" src="https://hits.sh/github.com/Saptha-me/Bindu.svg"></a>
</p>

<h4 align="center">
    <p>
        <a href="../README.md">English</a> |
        <a href="README.de.md">Deutsch</a> |
        <a href="README.es.md">Español</a> |
        <a href="README.fr.md">Français</a> |
        <a href="README.hi.md">हिंदी</a> |
        <a href="README.bn.md">বাংলা</a> |
        <a href="README.zh.md">中文</a> |
        <a href="README.nl.md">Nederlands</a> |
        <b>Bahasa Indonesia</b> |
        <a href="README.ta.md">தமிழ்</a>
    </p>
</h4>

<h3 align="center">Lapisan identitas, komunikasi, dan pembayaran untuk agen AI.</h3>

Situasinya seperti ini. Anda telah membangun sebuah agen AI. Agen tersebut berfungsi. Namun untuk benar-benar menerapkannya ke dunia luar — berkomunikasi dengan agen lain, membuktikan identitasnya, menerima pembayaran atas tugas yang diselesaikan — Anda harus menangani banyak infrastruktur teknis yang membosankan. Mengintegrasikan pustaka DID. Menyiapkan alur OAuth. Middleware pembayaran. Lapisan HTTP yang mengikuti protokol apa pun yang digunakan oleh ekosistem agen lainnya.

Bindu menyediakan semua infrastruktur teknis tersebut hanya dalam satu pemanggilan fungsi. Anda cukup membungkus handler Anda dengan `bindufy()`, dan beberapa detik kemudian agen Anda sudah online — lengkap dengan identitas kriptografisnya sendiri, mendukung protokol [A2A](https://github.com/a2aproject/A2A) (protokol yang digunakan oleh agen lain), dan siap meminta pembayaran USDC pada rantai EVM apa pun sebelum mengeksekusi tugas ([x402](https://github.com/coinbase/x402)). Handler Anda tetap sesederhana `(messages) -> response`. Framework di dalam handler — Agno, LangChain, CrewAI, atau buatan Anda sendiri — Bindu tidak membatasinya.

Tersedia SDK untuk Python, TypeScript, dan Kotlin, dan semuanya berbagi inti gRPC yang sama. Bahasa adalah pilihan Anda; protokol dan identitasnya tetap sama. Jika Anda ingin mempelajarinya lebih lanjut, [dokumentasi](https://docs.getbindu.com) adalah langkah berikutnya.

## Instalasi

Anda memerlukan Python 3.12+ dan [uv](https://github.com/astral-sh/uv).

```bash
uv add bindu
```

Jika Anda ingin berkontribusi langsung pada kode sumber Bindu:

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

Untuk menjalankan contoh (examples), Anda memerlukan kunci API untuk setidaknya satu penyedia LLM — `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, atau `MINIMAX_API_KEY`.

<br/>

## Panduan Cepat (Quickstart)

Bangun agen sesuai kebutuhan Anda, teruskan ke `bindufy()`, dan agen Anda langsung online. Contoh kode di bawah ini sudah lengkap — salin ke dalam berkas, atur `OPENAI_API_KEY` Anda, lalu jalankan.

```python
import os
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

agent = Agent(
    instructions="You are a research assistant.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

config = {
    "author": "you@example.com",
    "name": "research_agent",
    "description": "Research assistant with web search.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering"],
}

def handler(messages: list[dict[str, str]]):
    return agent.run(input=messages)

bindufy(config, handler)
```

Agen sekarang aktif di `http://localhost:3773`. `expose: True` akan membuka tunnel FRP sehingga seluruh internet dapat mengaksesnya tanpa perlu mengatur port forwarding.

<details>
<summary>Contoh dalam TypeScript</summary>

```typescript
import { bindufy } from "@bindu/sdk";
import OpenAI from "openai";

const openai = new OpenAI();

bindufy({
  author: "you@example.com",
  name: "research_agent",
  description: "Research assistant.",
  deployment: { url: "http://localhost:3773", expose: true },
  skills: ["skills/question-answering"],
}, async (messages) => {
  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: messages.map(m => ({ role: m.role as "user" | "assistant" | "system", content: m.content })),
  });
  return response.choices[0].message.content || "";
});
```

TypeScript SDK akan menjalankan core Python di latar belakang — Anda tidak perlu melihatnya dan tidak memerlukan kode Python di repositori Anda. Protokol yang sama, DID yang sama. Contoh lengkap di [`examples/typescript-openai-agent/`](../examples/typescript-openai-agent/).

</details>

<details>
<summary>Memanggil agen dengan curl</summary>

```bash
curl -X POST http://localhost:3773/ \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": "<uuid>",
    "params": {
      "message": {
        "role": "user",
        "kind": "message",
        "parts": [{"kind": "text", "text": "Hello"}],
        "messageId": "<uuid>",
        "contextId": "<uuid>",
        "taskId": "<uuid>"
      }
    }
  }'
```

Kemudian lakukan polling pada `tasks/get` dengan `taskId` yang sama sampai statusnya menjadi `completed`.

</details>

<br/>

## Keamanan: Tiga Lapisan, Aktif Secara Default

Sebagian besar framework agen menganggap keamanan sebagai tanggung jawab Anda. Bindu menganggapnya sebagai bagian dari transport.

Ketika permintaan A2A diterima oleh agen Bindu, tiga middleware berbeda dijalankan sebelum handler Anda melihat isi request — dan masing-masing menjawab pertanyaan yang tidak dapat dijawab oleh dua lainnya:

| Lapisan | Pertanyaan yang dijawab | Implementasi nyata |
|---|---|---|
| **mTLS** | _Apakah socket itu sendiri terenkripsi dan terotentikasi secara mutual?_ | Sertifikat X.509 dari [Smallstep step-ca](https://smallstep.com/docs/step-ca/), SAN = DID, masa berlaku 24 jam, diperbarui otomatis in-process |
| **OAuth2 via Hydra** | _Apakah pemanggil diizinkan untuk melakukan operasi ini saat ini?_ | Bearer token bergaya Ed, masa berlaku ~1 jam, divalidasi melalui introspeksi [Ory Hydra](https://www.ory.sh/hydra/) |
| **Tanda Tangan DID** | _Apakah isi JSON body ini benar-benar dibuat oleh DID yang diklaim?_ | Tanda tangan Ed25519 atas body kanonikal, dikirim dalam `X-DID-Signature` |

Anda tidak perlu memilih salah satu atau memasangnya secara manual. Ketiganya hadir bersama — dan pada agen pribadi operator, **aktif secara default sejak 2026.21.1**.

→ **Penjelasan lengkap:** [docs/SECURITY_STACK.md](../docs/SECURITY_STACK.md) menjelaskan fungsi setiap lapisan, alur request melalui ketiga lapisan, konfigurasi default saat ini, dan panduan troubleshooting.

<br/>

## Fitur

Setiap baris di bawah ini terhubung ke panduan lengkap yang mendalam.

| Fitur | Fungsi | Dokumentasi |
|---|---|---|
| **A2A JSON-RPC** | Protokol yang telah didukung oleh agen AI lainnya. `message/send`, `tasks/get`, `message/stream` pada port 3773. | — |
| **Transport mTLS** | Socket terenkripsi dan saling terotentikasi (mutual authentication). Setiap agen mendapatkan sertifikat X.509 dari step-ca (SAN = DID), menjalankan uvicorn via TLS, dan memperbarui sertifikat otomatis setiap ~16 jam. | [SECURITY_STACK.md](../docs/SECURITY_STACK.md) · [MTLS_DEPLOYMENT_GUIDE.md](../docs/MTLS_DEPLOYMENT_GUIDE.md) |
| **Identitas DID** | Setiap respons yang dikirim agen Anda ditandatangani dengan kunci Ed25519. Pemanggil memverifikasi dengan W3C DID — tanpa shared secret yang rentan bocor, dan DID yang sama berlaku untuk sertifikat SAN, OAuth2 client_id, serta penanda tangan pesan. | [DID.md](../docs/DID.md) |
| **OAuth2 via Hydra** | Token bearer dengan cakupan (scope) (`agent:read`, `agent:write`, `agent:execute`), bukan satu kunci tunggal untuk semua akses. | [AUTHENTICATION.md](../docs/AUTHENTICATION.md) |
| **Pembayaran x402** | Cukup aktifkan sebuah flag dan agen akan meminta pembayaran USDC sebelum handler Anda memproses request. **5 jaringan rantai pra-konfigurasi** — Base, Base Sepolia, Ethereum, Ethereum Sepolia, SKALE Europa — serta rantai EVM lainnya via `extra_networks`. | [PAYMENT.md](../docs/PAYMENT.md) |
| **Notifikasi Push** | Agen mengirim webhook saat status tugas berubah. Anda tidak perlu lagi melakukan polling berulang. | [NOTIFICATIONS.md](../docs/NOTIFICATIONS.md) |
| **Sistem Skills** | Deklarasikan kemampuan agen Anda; pemanggil dapat melihatnya pada agent card sebelum mengeluarkan token untuk bertanya. | [SKILLS.md](../docs/SKILLS.md) |
| **Private Skills** | Sembunyikan deskripsi skill komersial dari katalog publik. Crawler publik melihat deskripsi umum — DID mitra yang masuk allowlist dapat melihat daftar lengkap pada endpoint terotentikasi. | [PRIVATE_SKILLS.md](../docs/PRIVATE_SKILLS.md) |
| **Negosiasi Antar-Agen** | Dua agen dapat menyepakati harga, latensi, dan SLA di awal. Tanpa biaya tak terduga. | [NEGOTIATION.md](../docs/NEGOTIATION.md) |
| **Penyimpanan (Storage)** | Postgres untuk tugas dan pesan. Anda dapat mengganti backend sesuai kebutuhan. | [STORAGE.md](../docs/STORAGE.md) |
| **Scheduler** | Percobaan ulang (retries), batas waktu (timeouts), dan tugas berulang berbasis Redis. | [SCHEDULER.md](../docs/SCHEDULER.md) |
| **Tunnel Publik** | `expose: true` menghubungkan perangkat lokal Anda ke internet. Tanpa port forwarding atau konfigurasi router. | [TUNNELING.md](../docs/TUNNELING.md) |
| **SDK Multi-Bahasa** | Python, TypeScript, Kotlin — berbagi core gRPC yang sama di balik layar, DID yang sama, dan autentikasi yang sama. | [GRPC_LANGUAGE_AGNOSTIC.md](../docs/GRPC_LANGUAGE_AGNOSTIC.md) |
| **Deployment Cloud** | `bindu deploy agent.py --runtime=boxd` meluncurkan skrip Anda ke microVM dan mencetak URL HTTPS. Tanpa perlu Dockerfile. | [runtime/quickstart.md](../docs/runtime/quickstart.md) |
| **Gateway** | Planner LLM yang mengorkestrasi sekumpulan agen melalui A2A dan menyiarkan (stream) hasilnya kembali. | [GATEWAY.md](../docs/GATEWAY.md) |
| **Observabilitas** | Tracing OpenTelemetry, pelaporan error Sentry, dan endpoint health check. | [OBSERVABILITY.md](../docs/OBSERVABILITY.md) |

<br/>

## Demo

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Video demo Bindu" width="640" />
  </a>
</div>

Tersedia juga inbox operator bergaya Gmail di [`inbox/`](../inbox/). Jalankan dengan `cd inbox && npm run dev` dan buka `http://localhost:3775`.

<br/>

## Contoh (Examples)

Beberapa contoh dari [`examples/`](../examples/):

| Contoh | Yang Ditunjukkan |
|---|---|
| [Agent Swarm](../examples/agent_swarm/) | Sekelompok agen Agno yang saling mendelegasikan tugas satu sama lain. |
| [Premium Advisor](../examples/premium-advisor/) | Penggunaan x402 dalam praktik — pemanggil harus membayar USDC sebelum proses dijalankan. |
| [Hermes via Bindu](../examples/hermes_agent/) | Agen Hermes dari Nous Research yang diintegrasikan dengan Bindu dalam ~90 baris kode. |
| [Gateway Test Fleet](../examples/gateway_test_fleet/) | Lima agen dan satu gateway — alur multi-agen menyeluruh dari awal hingga akhir. |
| [TypeScript OpenAI Agent](../examples/typescript-openai-agent/) | Agen murni TypeScript tanpa dependensi Python di repositori Anda. |

Terdapat 20+ contoh lainnya yang mencakup analisis CSV, tanya jawab PDF, speech-to-text, web scraping, kolaborasi multibahasa, penulisan blog, dan banyak lagi. Lihat selengkapnya di [`examples/`](../examples/).

<br/>

## Mengapa Kami Membangun Bindu

Kami menggunakan Bindu di lingkungan produksi untuk membangun **Trade Compliance OS** — sekumpulan agen yang menangani CBAM, EUDR, kode HS, dan Paspor Produk Digital (Digital Product Passports), sehingga bisnis kecil-menengah (UKM) dapat mengirimkan kopi, tekstil, atau baja lintas negara tanpa perlu membayar biaya hukum yang sangat tinggi. Setiap agen dalam sistem tersebut terintegrasi dengan Bindu. Protokol, identitas, dan jalur pembayaran adalah masalah utama yang kami selesaikan melalui Bindu sejak awal.

Jika Anda membangun agen yang berkaitan dengan hal ini — dokumen kepabeanan, audit pemasok, pengadaan material, pelaporan regulasi, atau bidang terkait — kami sangat menyambut partisipasi Anda di jaringan ini. [Temukan kami di Discord](https://discord.gg/3w5zuYUuwt) untuk berdiskusi.

<br/>

## Framework yang Didukung

Gunakan framework apa pun yang Anda sukai untuk menulis agen. Bindu fleksibel terhadap apa yang ada di dalam handler Anda.

| Bahasa | Framework yang telah diuji di repositori ini |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2), [Agno](https://github.com/agno-agi/agno), [CrewAI](https://github.com/joaomdmoura/crewAI), [Hermes Agent](https://github.com/NousResearch/hermes-agent), [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), [Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node), [LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **Lainnya** | Melalui [core gRPC](../docs/grpc/) — SDK baru biasanya hanya membutuhkan beberapa ratus baris kode |

Jika penyedia model Anda mendukung API OpenAI atau Anthropic, maka akan langsung kompatibel — [OpenRouter](https://openrouter.ai/), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com), dan lainnya.

<br/>

## Dokumentasi

- [Situs Dokumentasi Lengkap](https://docs.getbindu.com)
- [Security stack — mTLS + Hydra + DID](../docs/SECURITY_STACK.md) — cara kerja ketiga lapisan identitas
- [Memanggil Agen Terproteksi](../docs/AUTH.md) — panduan ringkas autentikasi (token + tanda tangan DID)
- [Autentikasi (Lengkap)](../docs/AUTHENTICATION.md) dan [Tanda Tangan DID (Lengkap)](../docs/DID.md)
- [Panduan Deployment mTLS](../docs/MTLS_DEPLOYMENT_GUIDE.md) — panduan DevOps untuk penyiapan step-ca dan sertifikat
- [Deployment Cloud](../docs/runtime/quickstart.md) — panduan `bindu deploy`
- [Gateway](../docs/GATEWAY.md) — orkestrasi multi-agen
- [Private Skills](../docs/PRIVATE_SKILLS.md) — sembunyikan katalog komersial dari publik, tampilkan hanya ke mitra allowlist
- [Arsitektur gRPC](../docs/grpc/) — panduan untuk membangun SDK bahasa baru
- [Masalah yang Diketahui](../bugs/known-issues.md) — baca sebelum menerapkan ke produksi
- [Troubleshooting](../docs/AUTHENTICATION.md#troubleshooting) — penanganan kesalahan umum

<br/>

## Pengujian (Testing)

```bash
uv run pytest tests/unit/ -v                                    # unit test cepat
uv run pytest tests/integration/grpc/ -v -m e2e                 # E2E gRPC
uv run pytest -n auto --cov=bindu --cov-report=term-missing     # seluruh test suite
```

<br/>

## Kontribusi

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

Panduan lengkap ada di [`.github/contributing.md`](../.github/contributing.md). Diskusi sehari-hari berlangsung di [Discord](https://discord.gg/3w5zuYUuwt) — mari bergabung dan menyapa kami.

<br/>

## Pemelihara (Maintainers)

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/raahulrahl">
        <img src="https://github.com/raahulrahl.png?size=120" width="100" alt="Raahul Dutta" /><br />
        <sub><b>Raahul Dutta</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/Paraschamoli">
        <img src="https://github.com/Paraschamoli.png?size=120" width="100" alt="Paras Chamoli" /><br />
        <sub><b>Paras Chamoli</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/chandan-1427">
        <img src="https://github.com/chandan-1427.png?size=120" width="100" alt="Chandan" /><br />
        <sub><b>Chandan</b></sub>
      </a>
    </td>
  </tr>
</table>

<br/>

## Ucapan Terima Kasih (Acknowledgements)

Bindu dibangun di atas berbagai proyek open source yang luar biasa:

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

<br/>

## Riwayat Star

<a href="https://star-history.com/#getbindu/Bindu&Date">
  <img src="https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date" alt="Riwayat Star">
</a>

<br/>

## Lisensi

Apache 2.0. Lihat [LICENSE.md](../LICENSE.md).

<p align="center">
  <em>"Kami percaya pada teori bunga matahari — berdiri tegak bersama, membawa harapan dan cahaya bagi Internet of Agents."</em>
</p>
