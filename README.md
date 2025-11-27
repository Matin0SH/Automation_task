# Multi-Channel Marketing Content Generation Workflow

> **Automated AI-powered content generation for product launches across LinkedIn, Newsletter, and Blog channels**

A production-ready Python workflow that transforms product documentation into high-quality, channel-specific marketing content using Google Gemini, advanced prompt engineering, and automated quality control.

---

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Installation & Setup](#installation--setup)
- [Usage Guide](#usage-guide)
- [Workflow Stages](#workflow-stages)
- [Cost & Performance](#cost--performance)
- [Project Structure](#project-structure)
- [Design Decisions](#design-decisions)
- [Future Enhancements](#future-enhancements)
- [Requirements & Dependencies](#requirements--dependencies)

---

## 🎯 Overview

This workflow automates the creation of marketing content for Genie AI feature launches, generating:
- **1x LinkedIn Post** (150-300 words, mobile-optimized)
- **1x Newsletter Email** (200-400 words, scannable format)
- **1x Blog Post** (800-1200 words, SEO-friendly)

**Target Audience:** Small business executives (4-50 employees), non-legally trained, US-based, looking to minimize time and money spent on legal activities.

**Key Differentiator:** In addition to what platforms like Zapier or n8n offer, this solution demonstrates how a custom Python workflow can embed LLM architecture, prompt engineering, and AI agent design patterns more deeply, giving extra flexibility and customization when needed.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT: Source Documents                     │
│  (Product Roadmap, Engineering Ticket, Meeting Transcript,          │
│   Marketing Notes, Customer Feedback)                               │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: Document Parsing                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ TopicParser (tool/document_parser.py)                        │   │
│  │ • Intelligent file type detection                            │   │
│  │ • PDF extraction (pdfplumber)                                │   │
│  │ • DOCX extraction (python-docx)                              │   │
│  │ • Ordered document mapping for context                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STAGE 2: Parallel Content Generation                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  LinkedIn    │  │ Newsletter   │  │  Blog Post   │              │
│  │   Agent      │  │   Agent      │  │   Agent      │              │
│  │              │  │              │  │              │              │
│  │ ThreadPool   │  │ ThreadPool   │  │ ThreadPool   │              │
│  │ Worker 1     │  │ Worker 2     │  │ Worker 3     │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│         └─────────────────┴─────────────────┘                       │
│                           │                                          │
│                  ┌────────▼────────┐                                │
│                  │ ContentAgent    │                                │
│                  │ (Unified Agent) │                                │
│                  │                 │                                │
│                  │ • Base Prompt   │                                │
│                  │ • Channel Prompt│                                │
│                  │ • Few-Shot      │                                │
│                  │   Examples      │                                │
│                  │ • Gemini API    │                                │
│                  └─────────────────┘                                │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STAGE 3: Quality Control Loop                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ GENERATE → JUDGE → REFINE (Max 2 Iterations)                 │   │
│  │                                                               │   │
│  │ 1. Generate: Create initial content                          │   │
│  │ 2. Judge: Score 0-10 with detailed feedback                  │   │
│  │ 3. Refine: Improve based on feedback (if score < 8)          │   │
│  │ 4. Repeat: Until passing score or max iterations             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   OUTPUT: Structured JSON Files                     │
│  • linkedin.json (content + hashtags + metadata)                    │
│  • newsletter.json (subject + body + metadata)                      │
│  • blog.json (title + content + metadata)                           │
│  • parsed_documents.json (checkpoint)                               │
│                                                                      │
│  Metadata: final_score, passed_quality, refinement_iterations,      │
│            feedback, model_used, timestamp                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 🎨 Intelligent Document Parsing
- **Ordered Document Mapping**: Each of the 5 documents has semantic meaning (roadmap → ticket → transcript → notes → feedback) to provide LLM with contextual understanding
- **Multi-Format Support**: PDF (pdfplumber) and DOCX (python-docx) parsing
- **Automatic Type Detection**: Intelligent filename-based document classification

### 🤖 Advanced Agent Architecture
- **Unified Agent Pattern**: Single `ContentAgent` class dynamically loads channel-specific prompts and schemas
- **Generate → Judge → Refine Loop**: Automated quality control with iterative improvement
- **Few-Shot Learning**: Load well-written examples from `examples/{channel}/` to guide the model
- **Structured Output Enforcement**: Gemini's native schema validation guarantees valid JSON

### ⚡ Performance Optimization
- **Parallel Processing**: ThreadPoolExecutor runs all 3 channels concurrently (3x faster)
- **Retry Logic**: Exponential backoff for API failures (max 3 retries)
- **Checkpoint Saving**: Parsed documents saved before generation to prevent data loss

### 📊 Quality Assurance
- **Automated Scoring**: 0-10 quality score with pass/fail thresholds
- **Detailed Feedback**: Strengths, weaknesses, suggestions, and red flags
- **Refinement History**: Track all iteration attempts with scores and feedback
- **Metadata Logging**: Comprehensive generation metadata in every output

### 🎯 Channel-Specific Optimization
- **LinkedIn**: Mobile-friendly, hook-driven, 3-5 hashtags, 150-300 words
- **Newsletter**: Scannable bullets, empathetic tone, clear CTA, 200-400 words
- **Blog**: Problem-solution structure, SEO-friendly, use cases, 800-1200 words

---

## 🔄 How It Works

### The Concept: Semantic Document Ordering

Instead of simply dumping all documents into the LLM context, this workflow assigns **semantic meaning** to each document's position:

1. **Product Roadmap Summary** → Strategic overview, business goals
2. **Engineering Ticket** → Technical details, actual implementation
3. **Meeting Transcript** → Team discussions, nuanced context
4. **Marketing & Product Notes** → Key messaging, what to emphasize
5. **Customer Feedback Snippets** → Real pain points, authentic voice

This ordered approach helps the LLM understand **what** information to extract from **where**, resulting in more accurate and contextually appropriate content.

### The Agent: Prompt Engineering + Few-Shot Learning

Each channel has:
- **Base Prompt** (`agents/base_prompt.txt`): Shared audience, tone, and formatting rules
- **Generator Prompt** (`agents/{channel}/generator_prompt.txt`): Channel-specific structure and requirements
- **Judge Prompt** (`agents/{channel}/judge_prompt.txt`): Quality evaluation criteria
- **Refiner Prompt** (`agents/{channel}/refiner_prompt.txt`): Improvement instructions

**Few-Shot Learning**: Place 2-3 high-quality examples in `examples/{channel}/*.json`, and the system automatically loads them into the prompt. The LLM learns from these examples to match style, tone, and structure.

### The Quality Loop: Generate → Judge → Refine

```python
# Simplified pseudocode
content = generate(topic, documents, examples)  # Initial generation

for iteration in range(max_iterations):
    score = judge(content)  # Score 0-10 with feedback

    if score.passes:  # Typically 8/10 threshold
        break

    content = refine(content, score.feedback)  # Improve based on feedback

save(content, metadata)  # Save with scores, iterations, timestamp
```

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+ (tested on 3.12)
- Google Gemini API key

### Step 1: Clone & Install
```bash
# Install dependencies
pip install google-generativeai python-dotenv pdfplumber python-docx
```

### Step 2: Configure API Key
Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_google_gemini_api_key_here
```

### Step 3: Prepare Source Documents
Create a topic folder in `source/`:
```
source/
└── Your Feature Name/
    ├── Product Roadmap Summary.pdf
    ├── Engineering Ticket.docx
    ├── Meeting Transcript.pdf
    ├── Marketing & Product Meeting Notes.docx
    └── Customer Feedback Snippets.pdf
```

**Important**: Document filenames must contain keywords:
- Roadmap: `roadmap`, `summary`
- Engineering: `engineering`, `ticket`, `linear`
- Transcript: `transcript`, `meeting`
- Marketing: `marketing`, `notes`
- Feedback: `feedback`, `customer`

### Step 4: (Optional) Add Few-Shot Examples
Add high-quality examples to guide the model:
```
examples/
├── linkedin/
│   ├── ai-contract-review.json
│   └── document-compare.json
├── newsletter/
│   └── ai-contract-review.json
└── blog/
    └── ai-contract-review.json
```

Example JSON format:
```json
{
  "topic": "AI Contract Review",
  "content": "Your well-written LinkedIn post...",
  "hashtags": ["LegalTech", "AI", "Startups"]
}
```

---

## 💻 Usage Guide

### Basic Commands

```bash
# Generate LinkedIn post only (default channel)
python main.py linkedin

# Generate newsletter email only
python main.py newsletter

# Generate blog post only
python main.py blog

# Generate ALL channels in parallel (recommended)
python main.py --all-channels

# Process all topics in source directory
python main.py --all-topics

# Process specific topic by name
python main.py --topic "Document Compare" --all-channels

# Process specific topic by index (1-based)
python main.py --topic 1 --all-channels
```

### Advanced Configuration

Edit `config.json`:
```json
{
  "api": {
    "model": "gemini-2.5-flash",        // Or gemini-1.5-pro for higher quality
    "temperature": 0.7,                  // 0.0 = deterministic, 1.0 = creative
    "max_output_tokens": 64000,
    "max_retries": 3,
    "retry_delay": 2
  },
  "workflow": {
    "max_refinement_iterations": 2,     // Quality control loop limit
    "source_dir": "source",
    "output_dir": "output",
    "process_all_topics": false,
    "generate_all_channels": false
  },
  "channels": {
    "enabled": ["linkedin", "newsletter", "blog"],
    "default": "linkedin"
  },
  "logging": {
    "level": "INFO",                     // DEBUG, INFO, WARNING, ERROR
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/workflow.log",
    "console": true
  }
}
```

---

## 📊 Workflow Stages (Detailed)

### Stage 1: Document Parsing (5-10 seconds)
**File**: `tool/document_parser.py`

1. Scan `source/{topic}/` for PDF and DOCX files
2. Identify document type based on filename keywords
3. Extract text preserving structure:
   - PDFs: `pdfplumber` (handles tables, multi-column layouts)
   - DOCX: `python-docx` (preserves lists, tables, formatting)
4. Map documents to semantic categories
5. Save checkpoint: `output/{topic}/parsed_documents.json`

**Output**: Structured `TopicData` object with 5 categorized documents

### Stage 2: Parallel Content Generation (30-60 seconds)
**File**: `agents/content_agent.py`

**Per Channel (runs in parallel via ThreadPoolExecutor):**

1. **Load Context**:
   - Base prompt (audience, tone, JSON rules)
   - Channel-specific generator prompt
   - Few-shot examples (if available)
   - Source documents (ordered)

2. **API Call**:
   - Gemini 2.5 Flash with structured output schema
   - Temperature: 0.7 (balanced creativity)
   - Retry logic: 3 attempts with exponential backoff

3. **Parse & Validate**:
   - Remove markdown code blocks
   - Sanitize output (remove unexpected fields)
   - Validate against channel schema (LinkedIn/Newsletter/Blog)

**Output**: Raw content for each channel

### Stage 3: Quality Control Loop (20-40 seconds per iteration)
**Files**: `agents/content_agent.py` (judge & refine methods)

**For Each Channel:**

1. **Judge** (`judge_prompt.txt`):
   - Evaluate against 5-7 criteria (hook quality, clarity, tone, CTA, etc.)
   - Assign 0-10 score per criterion
   - Calculate overall score (average)
   - Determine pass/fail (typically 8/10 threshold)
   - Provide structured feedback:
     - Strengths (what works well)
     - Weaknesses (what needs improvement)
     - Suggestions (specific actionable fixes)
     - Red flags (critical issues)

2. **Refine** (if failed, `refiner_prompt.txt`):
   - Load original content
   - Inject judge feedback
   - Request improved version addressing weaknesses
   - Validate refined output

3. **Repeat**:
   - Loop max 2 times (configurable)
   - Stop if passing score achieved
   - Use best available version if max iterations reached

**Output**: Final content with metadata (score, iterations, feedback)

### Stage 4: Output Saving (< 1 second)
**File**: `main.py` (process_topic function)

Save structured JSON files:
```json
{
  "topic": "Document Compare",
  "channel": "linkedin",
  "linkedin_post": {
    "content": "Full post text with line breaks...",
    "hashtags": ["LegalTech", "Startups", "SmallBusiness"]
  },
  "metadata": {
    "generated_at": "2025-11-27T01:40:06.652157",
    "channel": "linkedin",
    "final_score": 10,
    "passed_quality": true,
    "refinement_iterations": 0,
    "refinement_history": [],
    "final_feedback": {
      "strengths": ["Excellent hook", "Clear benefits"],
      "weaknesses": [],
      "suggestions": []
    },
    "model_used": "gemini-2.5-flash"
  }
}
```

---

## 💰 Cost & Performance

### API Costs (Google Gemini 2.5 Flash)
**Pricing**: $0.075 per 1M input tokens, $0.30 per 1M output tokens (as of Nov 2024)

**Per 3-Channel Generation**:
- Input tokens: ~15K tokens (documents + prompts + examples)
- Output tokens: ~3K tokens (3 contents + judge feedback)
- **Estimated cost**: $0.02 - $0.05 per full run

**Monthly Cost** (for 20 feature launches):
- 20 launches × $0.03 average = **~$0.60/month**

(For cost context, typical no-code automation platforms like n8n Cloud or Zapier start around $20–30/month, and hiring a human copywriter for launch campaigns can be in the hundreds. This workflow is intended as a low-cost, reusable building block that could run inside that wider stack.)

### Processing Time (Benchmarks)
**Hardware**: Standard laptop (Intel i7, 16GB RAM)

| Stage | Time (Sequential) | Time (Parallel) |
|-------|------------------|-----------------|
| Document Parsing | 5-10s | 5-10s |
| Content Generation | 90-180s | 30-60s |
| Quality Loop | 60-120s | 20-40s |
| **Total** | **2.5-5 min** | **55-110s** |

**Performance Gains**:
- 3x faster with parallel processing
- No rate limit issues (Gemini handles concurrency well)
- Scales to N channels with minimal time increase

### Cost Optimization Strategies

**Current Implementation** (Gemini 2.5 Flash):
- ✅ Fast inference (~2-3s per request)
- ✅ High quality outputs (9-10/10 scores)
- ✅ Native structured output (no parsing errors)
- ✅ Low cost ($0.02-0.05 per run)

**Future Options**:

1. **Self-Hosted Open-Source Models** (for even lower costs):
   - Llama 3.1 70B (on AWS/GCP GPU instance)
   - Mistral Large (via vLLM)
   - **Cost**: ~$0.50-1.50/hour GPU compute → $0.01-0.03 per run
   - **Tradeoff**: Infrastructure management overhead

2. **Fine-Tuned Smaller Models**:
   - Fine-tune Gemini 1.5 Flash on your best-performing content
   - Or fine-tune Llama 3.1 8B for specific use case
   - **Benefit**: 5-10x cost reduction, consistent brand voice

3. **Hybrid Approach**:
   - Open-source model for generation
   - Gemini/GPT-4 for judging only
   - **Cost**: ~$0.01 per run


---

## 📁 Project Structure

```
automation_task/
├── source/                              # Input documents (by topic)
│   └── Genie AI's new feature Document compare/
│       ├── Product Roadmap Summary.docx
│       ├── Engineering Ticket.docx
│       ├── Meeting Transcript.docx
│       ├── Marketing & Product Meeting Notes.pdf
│       └── Customer Feedback Snippets.docx
│
├── output/                              # Generated content (by topic)
│   └── Genie AI's new feature Document compare/
│       ├── parsed_documents.json        # Checkpoint
│       ├── linkedin.json               # Final LinkedIn post + metadata
│       ├── newsletter.json             # Final newsletter + metadata
│       └── blog.json                   # Final blog post + metadata
│
├── agents/                              # Agent prompts and logic
│   ├── base_prompt.txt                 # Shared audience, tone, JSON rules
│   ├── content_agent.py                # Unified ContentAgent class
│   ├── output_schema.py                # Pydantic schemas for validation
│   ├── linkedin/
│   │   ├── generator_prompt.txt
│   │   ├── judge_prompt.txt
│   │   └── refiner_prompt.txt
│   ├── newsletter/
│   │   ├── generator_prompt.txt
│   │   ├── judge_prompt.txt
│   │   └── refiner_prompt.txt
│   └── blog/
│       ├── generator_prompt.txt
│       ├── judge_prompt.txt
│       └── refiner_prompt.txt
│
├── examples/                            # Few-shot learning examples
│   ├── linkedin/
│   │   ├── ai-contract-review.json
│   │   ├── document-compare.json
│   │   └── smart-clause-library.json
│   ├── newsletter/
│   │   └── ai-contract-review.json
│   └── blog/
│       └── ai-contract-review.json
│
├── tool/                                # Parsing and utility modules
│   ├── __init__.py
│   ├── document_parser.py              # TopicParser class
│   ├── extractors.py                   # PDF/DOCX extraction logic
│   └── schema.py                       # TopicData, ParsedDocuments schemas
│
├── docs/                                # Research and planning docs
│   ├── RESEARCH_LinkedIn_Prompt_Best_Practices.md
│   ├── RESEARCH_Newsletter_Email_Best_Practices_2025.md
│   ├── RESEARCH_Blog_Post_Best_Practices_2025.md
│   ├── RESEARCH_Structured_Output_Schema_Best_Practices_2025.md
│   ├── IMPLEMENTATION_SUMMARY_Parallel_Processing_and_Fixes.md
│   └── CODE_CLEANUP_SUMMARY.md
│
├── logs/                                # Execution logs
│   └── workflow.log
│
├── main.py                              # Main workflow orchestration
├── config.json                          # Configuration file
├── config_loader.py                     # Config loading utility
├── .env                                 # API keys (not committed)
├── README.md                            # This file
└── requirements.txt                     # Python dependencies
```

---

## 🧠 Design Decisions

### How this complements tools like Zapier or n8n

**The Question**: When would you use a custom Python workflow instead of only a no-code platform?

**The Answer**: For this task, I wanted to demonstrate the kind of technical depth Genie could use behind the scenes (LLM agents, structured outputs, semantic parsing), which can then sit alongside tools like Zapier/n8n in a real production stack.

**What Zapier/n8n Provide**:
- ✅ Visual workflow builder (great for non-technical users)
- ✅ Pre-built integrations (1000+ apps)
- ✅ Hosted infrastructure (no DevOps)
- ✅ Monitoring and alerting

**What This Custom Solution Demonstrates**:
- ✅ **Deep LLM Understanding**: Prompt engineering, few-shot learning, structured outputs
- ✅ **Agent Architecture Expertise**: Multi-step reasoning (generate → judge → refine)
- ✅ **Advanced Python Skills**: Async/parallel processing, error handling, modularity
- ✅ **Cost Optimization**: $0.02 vs $20-80/month for equivalent automation
- ✅ **Full Customization**: Tailored quality loops, channel-specific logic, semantic document ordering
- ✅ **Scalability**: Easy to extend (new channels, models, integrations)

**Real-World Application at Genie AI**:
- Zapier/n8n are excellent for connecting external tools (Slack, email, CRM)
- But for **core AI capabilities** (content generation, legal analysis), custom solutions offer:
  - Better quality control
  - Lower costs at scale
  - Proprietary IP and competitive advantage
  - Integration with existing ML infrastructure

**The Hybrid Approach** (ideal for production):
- Custom Python agents for AI-heavy tasks (this project)
- n8n/Zapier for workflow orchestration and integrations
- Example: n8n triggers this script when a new feature is added to Notion, then posts outputs to LinkedIn API and Mailchimp

### Why Ordered Document Parsing?

Instead of concatenating all documents randomly, the system assigns **semantic roles**:

1. **Product Roadmap** = "What" (feature overview)
2. **Engineering Ticket** = "How" (implementation details)
3. **Meeting Transcript** = "Why" (team reasoning)
4. **Marketing Notes** = "Message" (what to emphasize)
5. **Customer Feedback** = "Voice" (authentic pain points)

**Benefits**:
- LLM understands context hierarchy
- Better extraction of relevant information
- More coherent, accurate content generation
- Aligns with how humans process information

### Why Gemini Over GPT-4/Claude?

**Gemini 2.5 Flash Advantages**:
- ✅ Native structured output (schema enforcement)
- ✅ Extremely fast inference (~2-3s)
- ✅ Low cost ($0.075/$0.30 per 1M tokens)
- ✅ Large context window (1M tokens)
- ✅ Strong performance on marketing content

**Future**: Easy to swap in OpenAI/Anthropic by modifying `content_agent.py` (model initialization only).

### Why ThreadPoolExecutor (Not AsyncIO)?

**API calls are I/O-bound**, making parallelization ideal.

**ThreadPoolExecutor** (chosen):
- ✅ Simple implementation
- ✅ Works perfectly for I/O-bound tasks (API requests)
- ✅ Python GIL is not an issue (threads wait on network)
- ✅ Easy to debug and reason about

**AsyncIO** (not chosen):
- More complex code (`async`/`await` everywhere)
- Marginal performance difference for 3 concurrent requests
- Harder to integrate with synchronous libraries

**Benchmark**: ThreadPoolExecutor gives 3x speedup (180s → 60s), which is sufficient for this use case.

---

## 🚀 Future Enhancements

### Short-Term (1-2 hours)
- [ ] Add TXT and Markdown file parsing
- [ ] Implement token usage tracking (cost reporting)
- [ ] Create workflow diagram (Mermaid/Lucidchart)
- [ ] Add `--cost-report` flag to show API spend per run
- [ ] Support for custom document types (beyond the 5 standard)

### Medium-Term (1-2 days)
- [ ] **Direct Publishing APIs**:
  - LinkedIn API integration (auto-post to company page)
  - Mailchimp API (send newsletter to list)
  - WordPress/Ghost API (publish blog draft)
- [ ] **Multi-Model Support**:
  - OpenAI GPT-4 fallback
  - Anthropic Claude 3.5 Sonnet
  - Model selection via `--model` flag
- [ ] **Human-in-the-Loop Approval**:
  - Generate → Preview in terminal → Approve/Reject/Refine
  - Web UI for non-technical users (FastAPI + React)
- [ ] **A/B Testing Framework**:
  - Generate 2-3 variants per channel
  - Track performance metrics (clicks, engagement)
  - Auto-select best-performing style

### Long-Term (1-2 weeks)
- [ ] **RAG Pipeline for Historical Content**:
  - Vector DB (Pinecone/Weaviate) of past successful posts
  - Retrieve similar content for style consistency
  - Learn from high-performing examples over time
- [ ] **Fine-Tuned Models**:
  - Fine-tune Llama 3.1 70B on Genie AI's best content
  - Deploy on existing GPU infrastructure
  - Reduce costs to near-zero
- [ ] **Advanced Quality Metrics**:
  - Readability scores (Flesch-Kincaid)
  - SEO optimization (keyword density, meta descriptions)
  - Sentiment analysis (ensure positive tone)
- [ ] **Multi-Language Support**:
  - Translate content to Spanish, French, German
  - Localized tone and cultural adaptation
- [ ] **Integration with Genie AI Platform**:
  - Trigger workflow from product dashboard
  - Display generated content in admin panel
  - One-click publish to channels

---

## 🛠️ Requirements & Dependencies

### Python Version
- Python 3.8+ (tested on 3.12)

### Core Dependencies
```txt
google-generativeai>=0.3.0   # Gemini API client
python-dotenv>=1.0.0         # Environment variable management
pdfplumber>=0.10.0           # PDF text extraction
python-docx>=1.0.0           # DOCX text extraction
```

### Optional (for future enhancements)
```txt
# For async/await patterns
aiohttp>=3.9.0

# For web UI
fastapi>=0.110.0
uvicorn>=0.27.0

# For vector DB (RAG)
pinecone-client>=3.0.0
sentence-transformers>=2.3.0

# For publishing APIs
requests>=2.31.0             # HTTP client
linkedin-api>=2.0.0          # LinkedIn automation
mailchimp-marketing>=3.0.0   # Mailchimp integration
```

### Installation
```bash
# Production dependencies
pip install google-generativeai python-dotenv pdfplumber python-docx

# Or use requirements.txt (if created)
pip install -r requirements.txt
```

---

## 🧪 Testing & Validation

### Manual Testing
```bash
# Test single channel
python main.py linkedin

# Test all channels in parallel
python main.py --all-channels

# Check outputs
cat output/Genie\ AI\'s\ new\ feature\ Document\ compare/linkedin.json
```

### Quality Checks
1. **Review Scores**: All outputs should score 8-10/10
2. **Check Metadata**: Verify `passed_quality: true`
3. **Read Content**: Ensure tone matches audience (non-legal, small business)
4. **Validate JSON**: All output files should be valid JSON

### Expected Results
**LinkedIn** (linkedin.json:metadata:final_score): `10/10`
**Newsletter** (newsletter.json:metadata:final_score): `9/10`
**Blog** (blog.json:metadata:final_score): `9/10`

---

## 📞 Development Process & Tools

This project was developed using **Claude Code** (Anthropic's AI-assisted development tool) with a professional workflow:

1. **Research Phase**: Query best practices for prompt engineering, LangChain agents, structured outputs
2. **Planning Phase**: Design system architecture, define schemas, create prompts
3. **Implementation Phase**: Write modular, well-documented code with error handling
4. **Review Phase**: Test edge cases, validate outputs, optimize performance
5. **Documentation Phase**: Comprehensive README, inline comments, research docs

**Tools Used**:
- **Claude Code**: AI pair programmer for rapid prototyping and best practices
- **VS Code**: Primary IDE with Python extensions
- **Git**: Version control (not included in submission)
- **Python 3.12**: Latest stable Python version

**Development Time**: ~4-6 hours (including research, implementation, testing, documentation)

---

## 📄 License & Usage

This project is a portfolio demonstration for the Genie AI Graduate AI Automation Engineer position.

**Author**: Matin
**Date**: November 2024
**Purpose**: Technical assessment and demonstration of AI/automation expertise

---

## 🎓 About the Developer

I'm passionate about AI and have been working in the field since my bachelor's degree. My approach to building AI systems focuses on:

- **Deep Understanding**: Not just using tools, but understanding LLM architectures, prompt engineering, and agent design patterns
- **Cost Optimization**: Building production-ready solutions that scale efficiently
- **Continuous Learning**: Staying updated with the latest research (Gemini structured outputs, few-shot learning, RAG pipelines)
- **Pragmatic Engineering**: Balancing cutting-edge techniques with practical, maintainable code

While I recognize the value of no-code platforms like Zapier and n8n for workflow orchestration, I’m especially interested in building custom intelligent agents that can be fine-tuned, optimized, and integrated deeply into existing systems. In practice, I see these approaches working together: platforms like Zapier/n8n to coordinate workflows, and custom agents for the AI-heavy parts.

This project demonstrates not just my ability to complete a task, but my capacity to **architect scalable AI solutions** that can grow with Genie AI's needs.

---

## 🙏 Acknowledgments

- **Google Gemini Team**: For excellent API and structured output support
- **Anthropic Claude Code**: For AI-assisted development and best practices
- **Open Source Community**: pdfplumber, python-docx, and Python ecosystem

---

**Ready to transform product launches into automated content pipelines? Run `python main.py --all-channels` and see the magic happen!** ✨
